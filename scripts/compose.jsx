#targetengine "main"

// ======================================================
// MAGAZINEBOT — FINAL COMPOSE SCRIPT (2025) — FIXED
// Стабільний, без діалогів, ID 2020—2026+
// ВИПРАВЛЕНО: JSON fallback для InDesign 2026
// ======================================================

app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;

function log(msg) {
    try { $.writeln("[AIZINE] " + msg); } catch(e) {}
}

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
// IMAGE PLACEMENT
// ======================================================
function placeImage(frame, imgPath, fitType) {
    try {
        var img = ensureFile(imgPath);
        frame.place(img);

        if (fitType === "fill") {
            frame.fit(FitOptions.FILL_PROPORTIONALLY);
        } else {
            frame.fit(FitOptions.PROPORTIONALLY);
        }

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
            frames.push(item);
        }
    }

    // Sort by position (top-left first)
    frames.sort(function(a, b) {
        var boundsA = a.geometricBounds; // [top, left, bottom, right]
        var boundsB = b.geometricBounds;
        if (Math.abs(boundsA[0] - boundsB[0]) < 10) {
            return boundsA[1] - boundsB[1]; // same row, sort by left
        }
        return boundsA[0] - boundsB[0]; // sort by top
    });

    return frames;
}

function placeFallbackImages(doc, placements) {
    log("=== FALLBACK MODE: Placing images by page order ===");

    var placedCount = 0;
    var photoIndex = 0;

    for (var pageIdx = 0; pageIdx < doc.pages.length; pageIdx++) {
        if (photoIndex >= placements.length) break;

        var page = doc.pages[pageIdx];
        var frames = getImageFramesOnPage(page);

        log("Page " + (pageIdx + 1) + ": found " + frames.length + " image frames");

        // Place one photo per page (in the largest frame)
        if (frames.length > 0 && photoIndex < placements.length) {
            // Find largest frame by area
            var largestFrame = frames[0];
            var maxArea = 0;

            for (var f = 0; f < frames.length; f++) {
                var bounds = frames[f].geometricBounds;
                var area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]);
                if (area > maxArea) {
                    maxArea = area;
                    largestFrame = frames[f];
                }
            }

            var p = placements[photoIndex];
            log("  Placing " + p.filename + " into frame on page " + (pageIdx + 1));

            if (placeImage(largestFrame, p.photo, "fill")) {
                placedCount++;
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
    log("START MAGAZINEBOT COMPOSE (FIXED VERSION)");
    log("==============================================");

    var planPath = $.getenv("AIZINE_PLAN");
    if (!planPath) throw new Error("AIZINE_PLAN not set");

    log("PLAN = " + planPath);

    var plan = readJSON(planPath);
    var meta = plan.meta;
    var placements = plan.placements || [];
    var texts = plan.texts || {};

    log("Template = " + meta.template);

    // open template
    var tmpl = ensureFile(meta.template);
    var doc;

    try {
        doc = app.open(tmpl);
        log("Template opened OK");
    } catch(e) {
        throw new Error("Cannot open template: " + e.message);
    }

    // List all labels in document for debugging
    var existingLabels = listAllLabels(doc);

    // Calculate required pages and adjust document
    var requiredPages = meta.pages || calculateRequiredPages(placements);
    log("Required pages from meta: " + requiredPages);
    adjustPageCount(doc, requiredPages);

    // text
    for (var key in texts) {
        if (texts.hasOwnProperty(key)) {
            var txt = texts[key];
            if (txt) setTextByLabel(doc, key, txt);
        }
    }

    // ALWAYS use fallback - place images by page order
    // Label-based placement doesn't work reliably with this template
    log("Placing images by page order (fallback mode)...");
    var ok = placeFallbackImages(doc, placements);
    log("Total placed: " + ok + "/" + placements.length);

    // output
    var outDir = new Folder(meta.output_dir);
    if (!outDir.exists) outDir.create();

    var outIndd = new File(outDir.fsName + "/final.indd");
    var outPdf = new File(outDir.fsName + "/final.pdf");

    log("Saving INDD...");
    doc.save(outIndd);

    log("Exporting PDF...");
    var preset;
    try {
        preset = app.pdfExportPresets.itemByName("[High Quality Print]");
        if (!preset.isValid) throw "bad preset";
    } catch(e) {
        preset = app.pdfExportPresets[0];
    }

    try { preset.forceReadOnly = false; } catch(e) {}

    app.pdfExportPreferences.pageRange = PageRange.ALL_PAGES;
    doc.exportFile(ExportFormat.PDF_TYPE, outPdf, false, preset);

    doc.close(SaveOptions.NO);

    log("DONE: " + outPdf.fsName);
})();
