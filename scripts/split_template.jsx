#targetengine "main"

app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;

function log(msg) {
    try { $.writeln("[SPLITTER] " + msg); } catch(e) {}
}

function splitTemplateByArtboards(sourceFile, outputDir) {
    log("Opening source file: " + sourceFile);
    
    var doc = app.open(new File(sourceFile));
    var pages = doc.pages;
    log("Found " + pages.length + " pages/artboards");
    
    var outFolder = new Folder(outputDir);
    if (!outFolder.exists) outFolder.create();
    
    for (var i = 0; i < pages.length; i++) {
        var page = pages[i];
        log("Processing page/artboard " + (i + 1));
        
        try {
            var newDoc = app.documents.add({
                documentPreferences: {
                    pageWidth: page.bounds[3] - page.bounds[1],
                    pageHeight: page.bounds[2] - page.bounds[0],
                    facingPages: false,
                    pagesPerDocument: 1
                }
            });
            
            var newPage = newDoc.pages[0];
            var pageItems = page.allPageItems;
            
            for (var j = 0; j < pageItems.length; j++) {
                try {
                    var originalItem = pageItems[j];
                    var duplicatedItem = originalItem.duplicate(newPage);
                    
                    if (originalItem.label && originalItem.label.length > 0) {
                        duplicatedItem.label = originalItem.label;
                        log("Preserved label: " + originalItem.label);
                    }
                } catch(copyError) {
                    log("Error copying item: " + copyError.message);
                }
            }
            
            var fileName = "template_page_" + String(i + 1).padStart(2, '0') + ".indd";
            var outFile = new File(outFolder.fsName + "/" + fileName);
            
            newDoc.save(outFile);
            newDoc.close(SaveOptions.NO);
            log("Successfully saved: " + fileName);
            
        } catch(pageError) {
            log("Error processing page: " + pageError.message);
        }
    }
    
    doc.close(SaveOptions.NO);
    log("Template splitting completed!");
    alert("Splitting completed! Check output folder.");
}

(function(){
    try {
        var sourceFile = "C:/Projects/magazinebot/data/templates/lavstory/vesilnyi/vesilnyi.indd";
        var outputDir = "C:/Projects/magazinebot/data/templates/lavstory/vesilnyi_split/";
        splitTemplateByArtboards(sourceFile, outputDir);
    } catch(mainError) {
        log("Main error: " + mainError.message);
        alert("Error: " + mainError.message);
    }
})();
