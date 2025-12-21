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

    // text
    for (var key in texts) {
        if (texts.hasOwnProperty(key)) {
            var txt = texts[key];
            if (txt) setTextByLabel(doc, key, txt);
        }
    }

    // images
    log("Placing images...");
    var ok = 0;
    for (var i = 0; i < placements.length; i++) {
        var p = placements[i];
        if (placeImageByLabel(doc, p.label, p.photo, p.fit || "proportional")) ok++;
    }
    log("Placed " + ok + "/" + placements.length);

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
