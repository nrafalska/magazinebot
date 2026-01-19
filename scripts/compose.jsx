#targetengine "main"

// ======================================================
// MAGAZINEBOT — FINAL COMPOSE SCRIPT (2025) — FIXED
// Стабільний, без діалогів, ID 2020—2026+
// ВИПРАВЛЕНО: JSON fallback для InDesign 2026
// ======================================================

app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;

// Global log file for debugging
var _logFile = null;
var _logPath = "";

function getPlanPath() {
    // Try environment variable first
    var planPath = $.getenv("AIZINE_PLAN");
    if (planPath && planPath !== "null" && planPath !== "undefined") {
        return planPath;
    }

    // Try config file
    var configPath = $.getenv("AIZINE_CONFIG");
    if (!configPath) {
        configPath = Folder.temp.fsName + "/magazinebot_config.txt";
    }

    var configFile = new File(configPath);
    if (configFile.exists) {
        configFile.open("r");
        configFile.encoding = "UTF-8";
        planPath = configFile.read();
        configFile.close();
        return planPath.replace(/^\s+|\s+$/g, "");
    }

    return null;
}

function initLogFile() {
    try {
        // Get plan path to determine log location
        var planPath = getPlanPath();
        if (planPath) {
            var planFile = new File(planPath);
            _logPath = planFile.parent.fsName + "/compose_debug.log";
            _logFile = new File(_logPath);
            _logFile.open("w");
            _logFile.encoding = "UTF-8";
            _logFile.writeln("=== COMPOSE.JSX DEBUG LOG ===");
            _logFile.writeln("Started: " + new Date().toISOString());
            _logFile.writeln("Plan path: " + planPath);
            _logFile.writeln("Log path: " + _logPath);
            _logFile.writeln("");
        }
    } catch(e) {
        // Ignore - logging is optional
    }
}

function closeLogFile() {
    try {
        if (_logFile) {
            _logFile.writeln("");
            _logFile.writeln("Finished: " + new Date().toISOString());
            _logFile.close();
        }
    } catch(e) {}
}

function log(msg) {
    try { $.writeln("[AIZINE] " + msg); } catch(e) {}
    try {
        if (_logFile) {
            _logFile.writeln("[" + new Date().toTimeString().substr(0,8) + "] " + msg);
            // Flush immediately so we don't lose logs on crash
            _logFile.close();
            _logFile.open("a");
            _logFile.encoding = "UTF-8";
        }
    } catch(e) {}
}

// Initialize log file at script start
initLogFile();

// JSON fallback - ВИПРАВЛЕНО для InDesign 2026
if (typeof JSON === "undefined" || !JSON || !JSON.parse) {
    JSON = {
        parse: function(str) {
            try {
                // Безпечний eval для JSON
                return eval("(" + str + ")");
            } catch(e) {
                throw new Error("JSON parse failed: " + e.message);
            }
        }
    };
}

// ======================================================
// FILE TOOLS
// ======================================================
function readJSON(path) {
    var f = new File(path);
    if (!f.exists) throw new Error("JSON not found: " + path);

    f.open("r");
    f.encoding = "UTF-8";
    var txt = f.read();
    f.close();

    log("JSON content: " + txt.substring(0, 200) + "...");
    
    try {
        return JSON.parse(txt);
    } catch(e) {
        throw new Error("JSON parse error: " + e.message + " | Content: " + txt.substring(0, 100));
    }
}

function ensureFile(path) {
    var f = new File(path);
    if (!f.exists) throw new Error("Missing file: " + path);
    return f;
}

// ======================================================
// IMAGE PLACEMENT (IMPROVED)
// ======================================================
function placeImage(frame, imgPath, fitType, photoInfo) {
    try {
        var img = ensureFile(imgPath);
        frame.place(img);

        // Отримуємо розміри фрейму
        var frameBounds = frame.geometricBounds; // [top, left, bottom, right]
        var frameHeight = frameBounds[2] - frameBounds[0];
        var frameWidth = frameBounds[3] - frameBounds[1];
        var frameRatio = frameHeight / frameWidth;

        // Визначаємо орієнтацію фрейму
        var frameOrientation = "square";
        if (frameRatio > 1.2) {
            frameOrientation = "vertical";
        } else if (frameRatio < 0.8) {
            frameOrientation = "horizontal";
        }

        // Отримуємо орієнтацію фото (якщо передано)
        var photoOrientation = photoInfo ? photoInfo.orientation : null;

        log("Frame: " + frameWidth.toFixed(0) + "x" + frameHeight.toFixed(0) + " (" + frameOrientation + ")");
        if (photoOrientation) {
            log("Photo orientation: " + photoOrientation);
        }

        // Вибираємо найкращий спосіб вписування
        if (fitType === "fill") {
            // FILL_PROPORTIONALLY - заповнює фрейм, може обрізати
            frame.fit(FitOptions.FILL_PROPORTIONALLY);
        } else if (fitType === "fit") {
            // PROPORTIONALLY - вписує без обрізки, можуть бути поля
            frame.fit(FitOptions.PROPORTIONALLY);
        } else {
            // За замовчуванням - fill для кращого вигляду
            frame.fit(FitOptions.FILL_PROPORTIONALLY);
        }

        // Центруємо вміст
        frame.fit(FitOptions.CENTER_CONTENT);

        return true;

    } catch (e) {
        log("placeImage ERROR: " + e.message);
        return false;
    }
}

function placeImageByLabel(doc, label, imgPath, fitType) {
    var ok = false;

    // rectangles
    var rects = doc.rectangles;
    for (var i = 0; i < rects.length; i++) {
        if (rects[i].label === label) {
            if (placeImage(rects[i], imgPath, fitType)) ok = true;
        }
    }

    // fallback: all items
    if (!ok) {
        var items = doc.allPageItems;
        for (var j = 0; j < items.length; j++) {
            if (items[j].label === label) {
                if (placeImage(items[j], imgPath, fitType)) ok = true;
            }
        }
    }

    if (!ok) log("FRAME NOT FOUND: " + label);

    return ok;
}

// ======================================================
// TEXT
// ======================================================
function setTextByLabel(doc, label, txt) {
    var frames = doc.textFrames, found = false;
    for (var i = 0; i < frames.length; i++) {
        if (frames[i].label === label) {
            frames[i].contents = txt;
            found = true;
        }
    }
    if (!found) log("TEXT NOT FOUND: " + label);
    return found;
}

// ======================================================
// PAGE MANAGEMENT
// ======================================================
function calculateRequiredPages(placements) {
    // Cover = 1 page, Back = 1 page
    // Internal pages: parse PAGE_XX_IMG_YY labels
    var maxPage = 0;

    for (var i = 0; i < placements.length; i++) {
        var label = placements[i].label;

        if (label === "COVER_IMAGE") {
            // Cover is page 1
            if (maxPage < 1) maxPage = 1;
        } else if (label === "BACK_IMAGE") {
            // Back cover handled separately
        } else if (label.indexOf("PAGE_") === 0) {
            // Extract page number from PAGE_XX_IMG_YY
            var match = label.match(/PAGE_(\d+)_IMG/);
            if (match) {
                var pageNum = parseInt(match[1], 10) + 1; // +1 because cover is page 1
                if (pageNum > maxPage) maxPage = pageNum;
            }
        }
    }

    // Add 1 for back cover if we have BACK_IMAGE
    for (var j = 0; j < placements.length; j++) {
        if (placements[j].label === "BACK_IMAGE") {
            maxPage += 1;
            break;
        }
    }

    // Minimum 2 pages (cover + back), ensure even number for spreads
    if (maxPage < 2) maxPage = 2;
    if (maxPage % 2 !== 0) maxPage += 1;

    return maxPage;
}

function adjustPageCount(doc, targetPages) {
    var currentPages = doc.pages.length;
    log("Current pages: " + currentPages + ", Target: " + targetPages);

    // Get master spread for new pages
    var masterSpread = null;
    try {
        if (doc.masterSpreads.length > 0) {
            masterSpread = doc.masterSpreads[0];
            log("Found master spread: " + masterSpread.name);
        }
    } catch(e) {
        log("No master spread found: " + e.message);
    }

    // ADD pages if we need more
    if (currentPages < targetPages) {
        var pagesToAdd = targetPages - currentPages;
        log("Adding " + pagesToAdd + " pages with master...");

        for (var i = 0; i < pagesToAdd; i++) {
            try {
                var newPage = doc.pages.add();
                if (masterSpread) {
                    newPage.appliedMaster = masterSpread;
                }
            } catch(e) {
                log("Error adding page: " + e.message);
                break;
            }
        }
        log("Pages after adding: " + doc.pages.length);
        return;
    }

    // REMOVE pages if we have too many
    if (currentPages > targetPages) {
        var pagesToRemove = currentPages - targetPages;
        log("Removing " + pagesToRemove + " pages...");

        for (var i = 0; i < pagesToRemove; i++) {
            try {
                var lastPage = doc.pages[doc.pages.length - 1];
                lastPage.remove();
            } catch(e) {
                log("Error removing page: " + e.message);
                break;
            }
        }
        log("Pages after removal: " + doc.pages.length);
    }
}

function listAllLabels(doc) {
    log("=== ALL FRAME LABELS IN DOCUMENT ===");
    var items = doc.allPageItems;
    var labels = [];

    for (var i = 0; i < items.length; i++) {
        var lbl = items[i].label;
        if (lbl && lbl.length > 0) {
            labels.push(lbl);
        }
    }

    log("Found " + labels.length + " labeled frames:");
    for (var j = 0; j < labels.length; j++) {
        log("  - " + labels[j]);
    }
    log("=== END LABELS ===");

    return labels;
}

// ======================================================
// FALLBACK: Place images into rectangles by page order
// ======================================================
function getImageFramesOnPage(page) {
    var frames = [];
    var items = page.allPageItems;

    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        // Check if it's a rectangle that can hold an image
        if (item.constructor.name === "Rectangle" ||
            item.constructor.name === "Polygon" ||
            item.constructor.name === "Oval") {
            // Отримуємо інформацію про фрейм
            var bounds = item.geometricBounds; // [top, left, bottom, right]
            var height = bounds[2] - bounds[0];
            var width = bounds[3] - bounds[1];
            var ratio = height / width;

            var orientation = "square";
            if (ratio > 1.2) {
                orientation = "vertical";
            } else if (ratio < 0.8) {
                orientation = "horizontal";
            }

            frames.push({
                frame: item,
                width: width,
                height: height,
                area: width * height,
                orientation: orientation,
                bounds: bounds
            });
        }
    }

    // Sort by position (top-left first)
    frames.sort(function(a, b) {
        if (Math.abs(a.bounds[0] - b.bounds[0]) < 10) {
            return a.bounds[1] - b.bounds[1]; // same row, sort by left
        }
        return a.bounds[0] - b.bounds[0]; // sort by top
    });

    return frames;
}

function findBestFrameForPhoto(frames, photoOrientation) {
    /**
     * Знаходить найкращий фрейм для фото з урахуванням орієнтації.
     * Пріоритет:
     * 1. Фрейм з такою ж орієнтацією (найбільший за площею)
     * 2. Якщо немає - найбільший фрейм
     */
    if (frames.length === 0) return null;

    // Шукаємо фрейми з відповідною орієнтацією
    var matchingFrames = [];
    for (var i = 0; i < frames.length; i++) {
        if (frames[i].orientation === photoOrientation) {
            matchingFrames.push(frames[i]);
        }
    }

    // Якщо є фрейми з відповідною орієнтацією - беремо найбільший
    if (matchingFrames.length > 0) {
        var bestMatch = matchingFrames[0];
        for (var j = 1; j < matchingFrames.length; j++) {
            if (matchingFrames[j].area > bestMatch.area) {
                bestMatch = matchingFrames[j];
            }
        }
        log("  Found matching orientation frame: " + bestMatch.orientation + " (" + bestMatch.width.toFixed(0) + "x" + bestMatch.height.toFixed(0) + ")");
        return bestMatch;
    }

    // Інакше беремо найбільший фрейм
    var largest = frames[0];
    for (var k = 1; k < frames.length; k++) {
        if (frames[k].area > largest.area) {
            largest = frames[k];
        }
    }
    log("  No matching orientation, using largest frame: " + largest.orientation + " (" + largest.width.toFixed(0) + "x" + largest.height.toFixed(0) + ")");
    return largest;
}

function placeFallbackImages(doc, placements) {
    log("=== IMPROVED FALLBACK: Placing images with orientation matching ===");

    var placedCount = 0;
    var photoIndex = 0;

    for (var pageIdx = 0; pageIdx < doc.pages.length; pageIdx++) {
        if (photoIndex >= placements.length) break;

        var page = doc.pages[pageIdx];
        var frames = getImageFramesOnPage(page);

        log("Page " + (pageIdx + 1) + ": found " + frames.length + " image frames");

        if (frames.length > 0 && photoIndex < placements.length) {
            var p = placements[photoIndex];

            // Визначаємо орієнтацію фото з placement (якщо є)
            var photoOrientation = p.orientation || "unknown";
            log("  Photo: " + p.filename + " (" + photoOrientation + ")");

            // Знаходимо найкращий фрейм для цього фото
            var bestFrame = findBestFrameForPhoto(frames, photoOrientation);

            if (bestFrame) {
                log("  Placing into frame on page " + (pageIdx + 1));
                if (placeImage(bestFrame.frame, p.photo, "fill", {orientation: photoOrientation})) {
                    placedCount++;
                }
            }
            photoIndex++;
        }
    }

    log("=== FALLBACK: Placed " + placedCount + "/" + placements.length + " images ===");
    return placedCount;
}

// ======================================================
// MAIN
// ======================================================
(function(){

    log("==============================================");
    log("START MAGAZINEBOT COMPOSE (DEBUG VERSION)");
    log("==============================================");

    var planPath, plan, meta, placements, texts, tmpl, doc;

    // STEP 1: Get plan path (try env var first, then config file)
    try {
        log("STEP 1: Getting plan path...");
        planPath = getPlanPath();
        if (!planPath) throw new Error("AIZINE_PLAN not set and config file not found");
        log("STEP 1 OK: PLAN = " + planPath);
    } catch(e) {
        throw new Error("STEP 1 FAILED (env/config): " + e.message);
    }

    // STEP 2: Read JSON plan
    try {
        log("STEP 2: Reading JSON plan...");
        plan = readJSON(planPath);
        log("STEP 2 OK: JSON loaded");
    } catch(e) {
        throw new Error("STEP 2 FAILED (JSON): " + e.message);
    }

    // STEP 3: Extract meta
    try {
        log("STEP 3: Extracting meta...");
        meta = plan.meta;
        if (!meta) throw new Error("meta is null");
        placements = plan.placements || [];
        texts = plan.texts || {};
        log("STEP 3 OK: template=" + meta.template + ", placements=" + placements.length);
    } catch(e) {
        throw new Error("STEP 3 FAILED (meta): " + e.message);
    }

    // STEP 4: Check template file
    try {
        log("STEP 4: Checking template file...");
        log("STEP 4a: Template path from meta: " + meta.template);

        // Normalize path - convert backslashes to forward slashes
        var templatePath = meta.template;
        if (templatePath) {
            templatePath = templatePath.replace(/\\/g, "/");
        }
        log("STEP 4b: Normalized path: " + templatePath);

        log("STEP 4c: Creating File object...");
        tmpl = new File(templatePath);
        log("STEP 4d: File object created");

        log("STEP 4e: Checking if file exists...");
        if (!tmpl.exists) {
            log("STEP 4e: File does NOT exist!");
            throw new Error("Template file not found: " + templatePath);
        }
        log("STEP 4f: File exists: " + tmpl.exists);
        log("STEP 4 OK: Template path: " + tmpl.fsName);
    } catch(e) {
        closeLogFile();
        throw new Error("STEP 4 FAILED (template): " + e.message);
    }

    // STEP 5: Open template
    try {
        log("STEP 5: Opening template in InDesign...");
        doc = app.open(tmpl);
        if (!doc) throw new Error("doc is null after open");
        log("STEP 5 OK: Document opened, pages=" + doc.pages.length);
    } catch(e) {
        throw new Error("STEP 5 FAILED (open): " + e.message);
    }

    // STEP 6: List labels (optional debug)
    try {
        log("STEP 6: Listing labels...");
        var existingLabels = listAllLabels(doc);
        log("STEP 6 OK: Found " + existingLabels.length + " labels");
    } catch(e) {
        log("STEP 6 WARNING (labels): " + e.message);
        // Continue anyway
    }

    // STEP 7: Adjust page count
    try {
        log("STEP 7: Adjusting page count...");
        var requiredPages = meta.pages || calculateRequiredPages(placements);
        log("STEP 7: Required pages = " + requiredPages);
        adjustPageCount(doc, requiredPages);
        log("STEP 7 OK: Pages adjusted to " + doc.pages.length);
    } catch(e) {
        throw new Error("STEP 7 FAILED (pages): " + e.message);
    }

    // STEP 8: Set texts
    try {
        log("STEP 8: Setting texts...");
        for (var key in texts) {
            if (texts.hasOwnProperty(key)) {
                var txt = texts[key];
                if (txt) setTextByLabel(doc, key, txt);
            }
        }
        log("STEP 8 OK: Texts set");
    } catch(e) {
        log("STEP 8 WARNING (texts): " + e.message);
        // Continue anyway
    }

    // STEP 9: Place images
    try {
        log("STEP 9: Placing images (fallback mode)...");
        var ok = placeFallbackImages(doc, placements);
        log("STEP 9 OK: Placed " + ok + "/" + placements.length);
    } catch(e) {
        throw new Error("STEP 9 FAILED (images): " + e.message);
    }

    // STEP 10: Create output directory
    try {
        log("STEP 10: Creating output directory...");
        var outDir = new Folder(meta.output_dir);
        if (!outDir.exists) outDir.create();
        log("STEP 10 OK: " + outDir.fsName);
    } catch(e) {
        throw new Error("STEP 10 FAILED (outdir): " + e.message);
    }

    // STEP 11: Save INDD
    try {
        log("STEP 11: Saving INDD...");
        var outIndd = new File(outDir.fsName + "/final.indd");
        doc.save(outIndd);
        log("STEP 11 OK: " + outIndd.fsName);
    } catch(e) {
        throw new Error("STEP 11 FAILED (save): " + e.message);
    }

    // STEP 12: Export PDF
    try {
        log("STEP 12: Exporting PDF...");
        var outPdf = new File(outDir.fsName + "/final.pdf");

        var preset;
        try {
            preset = app.pdfExportPresets.itemByName("[High Quality Print]");
            if (!preset.isValid) throw "bad preset";
        } catch(e2) {
            preset = app.pdfExportPresets[0];
        }

        try { preset.forceReadOnly = false; } catch(e3) {}

        app.pdfExportPreferences.pageRange = PageRange.ALL_PAGES;
        doc.exportFile(ExportFormat.PDF_TYPE, outPdf, false, preset);
        log("STEP 12 OK: " + outPdf.fsName);
    } catch(e) {
        throw new Error("STEP 12 FAILED (pdf): " + e.message);
    }

    // STEP 13: Close document
    try {
        log("STEP 13: Closing document...");
        doc.close(SaveOptions.NO);
        log("STEP 13 OK");
    } catch(e) {
        log("STEP 13 WARNING (close): " + e.message);
    }

    log("==============================================");
    log("DONE SUCCESSFULLY");
    log("==============================================");

    closeLogFile();
})();
