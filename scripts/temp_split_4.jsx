#target indesign

// Відключити всі діалоги
app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;

var sourceFile = "C:/Projects/magazinebot/data/templates/for_her/filmy/filmy.indd";
var outputDir = "C:/Projects/magazinebot/data/templates/for_her/filmy";
var resultPath = "C:/Users/ashie/AppData/Local/Temp/indesign_result_4.txt";

function writeResult(message) {
    var f = new File(resultPath);
    f.open("w");
    f.write(message);
    f.close();
}

try {
    // Відкрити без відновлення
    var doc = app.open(File(sourceFile), false);
    var pages = doc.pages;
    var pageGroups = {};
    
    for (var i = 0; i < pages.length; i++) {
        var match = pages[i].name.match(/(\d+)\s*@\s*(\d+)%/);
        if (match) {
            var fillPercent = match[2];
            if (!pageGroups[fillPercent]) pageGroups[fillPercent] = [];
            pageGroups[fillPercent].push(i);
        }
    }
    
    var created = 0;
    
    for (var fillPercent in pageGroups) {
        var newDoc = app.documents.add();
        var indices = pageGroups[fillPercent];
        
        for (var j = 0; j < indices.length; j++) {
            var originalPage = doc.pages[indices[j]];
            if (j > 0) newDoc.pages.add();
            var newPage = newDoc.pages[j];
            var items = originalPage.pageItems;
            
            for (var k = items.length - 1; k >= 0; k--) {
                items[k].duplicate(newPage);
            }
        }
        
        var outFile = new File(outputDir + "/template_" + fillPercent + ".indd");
        newDoc.save(outFile);
        newDoc.close(SaveOptions.NO);
        created++;
    }
    
    doc.close(SaveOptions.NO);
    writeResult("SUCCESS:" + created);
    
} catch (e) {
    writeResult("ERROR:" + e.message + " (line " + e.line + ")");
}

app.quit(SaveOptions.NO);
