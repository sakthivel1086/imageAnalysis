for the below given code

// ===== CONFIGURATION =====
const CLARIFAI_API_KEY = 'YOUR_API_KEY_HERE'; // <-- Replace with your actual Clarifai API key

// Map image types to Clarifai model IDs and confidence thresholds
const MODEL_MAP = {
  'Grill':       { id: 'grill-temp-model-id', threshold: 0.93 },
  'Piping':      { id: 'piping-model-id', threshold: 0.92 },
  'ST IDU':      { id: 'st-idu-model-id', threshold: 0.90 },
  'ODU Install': { id: 'odu-install-model-id', threshold: 0.91 },
  'SR No':       { id: 'srno-model-id', threshold: 0.94 }
};

// ===== MAIN BATCH VALIDATION FUNCTION =====
function runImageComplianceCheck() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Sheet1");
  const data = sheet.getDataRange().getValues();
  const outputColumn = 3; // Column C (Result column)

  const groupedInputs = {};

  // Group inputs by model for batch API calls
  for (let i = 1; i < data.length; i++) {
    const url = data[i][0];
    const type = data[i][1];
    const result = data[i][outputColumn - 1];

    if (!url || !type || result) continue; // Skip if missing or already processed

    const modelConfig = MODEL_MAP[type];
    if (!modelConfig) {
      sheet.getRange(i + 1, outputColumn).setValue("❌ Unknown type");
      continue;
    }

    const modelId = modelConfig.id;
    if (!groupedInputs[modelId]) groupedInputs[modelId] = { inputs: [], rows: [], threshold: modelConfig.threshold };

    groupedInputs[modelId].inputs.push({ data: { image: { url: url } } });
    groupedInputs[modelId].rows.push(i + 1);
  }

  // Process each group in batches (max 128 per Clarifai API limit)
  for (const modelId in groupedInputs) {
    const group = groupedInputs[modelId];
    for (let i = 0; i < group.inputs.length; i += 128) {
      const inputBatch = group.inputs.slice(i, i + 128);
      const rowBatch = group.rows.slice(i, i + 128);
      const results = callClarifaiModel(modelId, inputBatch, group.threshold);

      for (let j = 0; j < results.length; j++) {
        sheet.getRange(rowBatch[j], outputColumn).setValue(results[j]);
      }
      Utilities.sleep(1500); // Sleep to avoid rate limits
    }
  }
}

// ===== CALL CLARIFAI API =====
function callClarifaiModel(modelId, inputBatch, threshold) {
  const url = https://api.clarifai.com/v2/models/${modelId}/outputs;
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Key ' + CLARIFAI_API_KEY },
    payload: JSON.stringify({ inputs: inputBatch }),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  const results = [];

  if (response.getResponseCode() === 200) {
    const outputs = JSON.parse(response.getContentText()).outputs;
    for (const output of outputs) {
      const concepts = output.data.concepts || [];
      // Find concept with confidence >= threshold
      const highConfidence = concepts.find(c => c.value >= threshold);
      if (highConfidence) {
        results.push(✅ ${highConfidence.name} (${(highConfidence.value * 100).toFixed(1)}%));
      } else {
        results.push("❌ Non-compliant or unclear");
      }
    }
  } else {
    const errText = response.getContentText();
    results.push(...Array(inputBatch.length).fill("❌ API Error: " + errText));
  }
  return results;
}

// ===== DASHBOARD GENERATOR =====
function generateComplianceDashboard() {
  const inputSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Sheet1");
  const dashboard = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Dashboard") ||
                    SpreadsheetApp.getActiveSpreadsheet().insertSheet("Dashboard");
  dashboard.clear();
  dashboard.appendRow(["Image Type", "✅ Passed", "❌ Failed", "⚠️ Manual Review"]);

  const data = inputSheet.getDataRange().getValues();
  const summary = {};

  for (let i = 1; i < data.length; i++) {
    const type = data[i][1];
    const result = data[i][2] || "";

    if (!summary[type]) summary[type] = { pass: 0, fail: 0, warn: 0 };

    if (result.includes("✅")) summary[type].pass++;
    if (result.includes("❌")) summary[type].fail++;
    if (result.includes("⚠️")) summary[type].warn++;
  }

  for (const type in summary) {
    const row = summary[type];
    dashboard.appendRow([type, row.pass, row.fail, row.warn]);
  }
}