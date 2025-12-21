try {
    alert("ExtendScript Test Started");
    
    var planPath = $.getenv("AIZINE_PLAN");
    alert("Plan path: " + planPath);
    
    if (!planPath) {
        alert("ERROR: AIZINE_PLAN not set");
    } else {
        // Тест читання файлу
        var planFile = new File(planPath);
        alert("Plan file exists: " + planFile.exists);
        
        if (planFile.exists) {
            planFile.open("r");
            planFile.encoding = "UTF-8";
            var content = planFile.read();
            planFile.close();
            
            alert("Plan content length: " + content.length);
            
            try {
                var plan = JSON.parse(content);
                alert("JSON parsed OK");
                alert("Template: " + plan.meta.template);
                
                // Тест шаблону
                var tmplFile = new File(plan.meta.template);
                alert("Template exists: " + tmplFile.exists);
                
            } catch (e) {
                alert("JSON parse error: " + e.message);
            }
        }
    }
    
    alert("Test completed");
    
} catch (e) {
    alert("ERROR: " + e.message + " at line " + e.line);
}