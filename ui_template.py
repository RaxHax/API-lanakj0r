"""
HTML Template for Multi-Bank Interest Rate API Test UI
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Bank Interest Rate API - Test Interface</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            color: #2d3748;
            font-size: 32px;
            margin-bottom: 10px;
        }

        .header p {
            color: #718096;
            font-size: 16px;
        }

        .banks-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .bank-card {
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .bank-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.15);
        }

        .bank-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .bank-name {
            font-size: 24px;
            font-weight: 700;
            color: #2d3748;
        }

        .bank-id {
            font-size: 12px;
            color: #718096;
            background: #edf2f7;
            padding: 4px 10px;
            border-radius: 12px;
        }

        .status-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 15px;
        }

        .status-idle {
            background: #e6fffa;
            color: #047857;
        }

        .status-loading {
            background: #fef3c7;
            color: #b45309;
        }

        .status-success {
            background: #d1fae5;
            color: #065f46;
        }

        .status-error {
            background: #fee2e2;
            color: #991b1b;
        }

        .status-cached {
            background: #dbeafe;
            color: #1e40af;
        }

        .button-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .btn {
            flex: 1;
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #edf2f7;
            color: #2d3748;
        }

        .btn-secondary:hover:not(:disabled) {
            background: #e2e8f0;
        }

        .response-box {
            background: #1a202c;
            border-radius: 10px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            line-height: 1.6;
            color: #e2e8f0;
        }

        .response-box::-webkit-scrollbar {
            width: 8px;
        }

        .response-box::-webkit-scrollbar-track {
            background: #2d3748;
            border-radius: 10px;
        }

        .response-box::-webkit-scrollbar-thumb {
            background: #4a5568;
            border-radius: 10px;
        }

        .response-box pre {
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .info-box {
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }

        .info-title {
            font-size: 20px;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 15px;
        }

        .endpoint {
            background: #f7fafc;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 6px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
        }

        .endpoint-method {
            color: #667eea;
            font-weight: 600;
            margin-right: 10px;
        }

        .loading-spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .meta-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }

        .meta-item {
            background: #f7fafc;
            padding: 10px;
            border-radius: 8px;
        }

        .meta-label {
            font-size: 11px;
            color: #718096;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .meta-value {
            font-size: 14px;
            color: #2d3748;
            font-weight: 600;
        }

        .all-banks-section {
            margin-top: 30px;
        }

        .section-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, white, transparent);
            margin: 40px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏦 Multi-Bank Interest Rate API</h1>
            <p>Test interface for Icelandic bank interest rate scrapers</p>
        </div>

        <div class="banks-grid">
            <!-- Landsbankinn -->
            <div class="bank-card" id="card-landsbankinn">
                <div class="bank-header">
                    <div>
                        <div class="bank-name">Landsbankinn</div>
                        <span class="bank-id">landsbankinn</span>
                    </div>
                </div>
                <div class="status-badge status-idle" id="status-landsbankinn">Ready</div>
                <div class="meta-info" id="meta-landsbankinn" style="display: none;"></div>
                <div class="button-group">
                    <button class="btn btn-primary" onclick="fetchBank('landsbankinn')">
                        <span id="btn-text-landsbankinn">Fetch Rates</span>
                    </button>
                    <button class="btn btn-secondary" onclick="refreshBank('landsbankinn')">
                        Force Refresh
                    </button>
                </div>
                <div class="response-box" id="response-landsbankinn">
                    <pre>Click "Fetch Rates" to load data...</pre>
                </div>
            </div>

            <!-- Arion banki -->
            <div class="bank-card" id="card-arionbanki">
                <div class="bank-header">
                    <div>
                        <div class="bank-name">Arion banki</div>
                        <span class="bank-id">arionbanki</span>
                    </div>
                </div>
                <div class="status-badge status-idle" id="status-arionbanki">Ready</div>
                <div class="meta-info" id="meta-arionbanki" style="display: none;"></div>
                <div class="button-group">
                    <button class="btn btn-primary" onclick="fetchBank('arionbanki')">
                        <span id="btn-text-arionbanki">Fetch Rates</span>
                    </button>
                    <button class="btn btn-secondary" onclick="refreshBank('arionbanki')">
                        Force Refresh
                    </button>
                </div>
                <div class="response-box" id="response-arionbanki">
                    <pre>Click "Fetch Rates" to load data...</pre>
                </div>
            </div>

            <!-- Íslandsbanki -->
            <div class="bank-card" id="card-islandsbanki">
                <div class="bank-header">
                    <div>
                        <div class="bank-name">Íslandsbanki</div>
                        <span class="bank-id">islandsbanki</span>
                    </div>
                </div>
                <div class="status-badge status-idle" id="status-islandsbanki">Ready</div>
                <div class="meta-info" id="meta-islandsbanki" style="display: none;"></div>
                <div class="button-group">
                    <button class="btn btn-primary" onclick="fetchBank('islandsbanki')">
                        <span id="btn-text-islandsbanki">Fetch Rates</span>
                    </button>
                    <button class="btn btn-secondary" onclick="refreshBank('islandsbanki')">
                        Force Refresh
                    </button>
                </div>
                <div class="response-box" id="response-islandsbanki">
                    <pre>Click "Fetch Rates" to load data...</pre>
                </div>
            </div>
        </div>

        <div class="section-divider"></div>

        <div class="all-banks-section">
            <div class="info-box">
                <div class="info-title">🚀 Fetch All Banks</div>
                <div class="button-group">
                    <button class="btn btn-primary" onclick="fetchAllBanks()" id="btn-all">
                        <span id="btn-text-all">Fetch All Banks</span>
                    </button>
                    <button class="btn btn-secondary" onclick="refreshAllBanks()">
                        Force Refresh All
                    </button>
                </div>
                <div class="response-box" id="response-all">
                    <pre>Click "Fetch All Banks" to load all bank data at once...</pre>
                </div>
            </div>
        </div>

        <div class="section-divider"></div>

        <div class="info-box">
            <div class="info-title">📡 API Endpoints</div>
            <div class="endpoint">
                <span class="endpoint-method">GET</span> /api/rates?bank=landsbankinn
            </div>
            <div class="endpoint">
                <span class="endpoint-method">GET</span> /api/rates?bank=arionbanki
            </div>
            <div class="endpoint">
                <span class="endpoint-method">GET</span> /api/rates?bank=islandsbanki
            </div>
            <div class="endpoint">
                <span class="endpoint-method">GET</span> /api/rates (all banks)
            </div>
            <div class="endpoint">
                <span class="endpoint-method">GET</span> /api/rates/refresh?bank=&lt;bank_id&gt;
            </div>
            <div class="endpoint">
                <span class="endpoint-method">GET</span> /api/rates/refresh (all banks)
            </div>
            <div class="endpoint">
                <span class="endpoint-method">GET</span> /health
            </div>
        </div>
    </div>

    <script>
        function updateStatus(bankId, status, text) {
            const statusEl = document.getElementById(`status-${bankId}`);
            statusEl.className = `status-badge status-${status}`;
            statusEl.textContent = text;
        }

        function updateMeta(bankId, data) {
            const metaEl = document.getElementById(`meta-${bankId}`);
            if (!data) {
                metaEl.style.display = 'none';
                return;
            }

            metaEl.style.display = 'grid';
            metaEl.innerHTML = `
                <div class="meta-item">
                    <div class="meta-label">Effective Date</div>
                    <div class="meta-value">${data.effective_date || 'N/A'}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Source</div>
                    <div class="meta-value">${data.cached ? 'Cached' : 'Fresh'}</div>
                </div>
            `;
        }

        function updateResponse(bankId, data) {
            const responseEl = document.getElementById(`response-${bankId}`);
            responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }

        function setLoading(bankId, isLoading) {
            const btnText = document.getElementById(`btn-text-${bankId}`);
            const buttons = document.querySelectorAll(`#card-${bankId} .btn`);

            if (isLoading) {
                btnText.innerHTML = '<span class="loading-spinner"></span>';
                buttons.forEach(btn => btn.disabled = true);
            } else {
                btnText.textContent = 'Fetch Rates';
                buttons.forEach(btn => btn.disabled = false);
            }
        }

        async function fetchBank(bankId) {
            updateStatus(bankId, 'loading', 'Fetching...');
            setLoading(bankId, true);

            try {
                const response = await fetch(`/api/rates?bank=${bankId}`);
                const data = await response.json();

                if (response.ok) {
                    updateStatus(bankId, data.cached ? 'cached' : 'success',
                        data.cached ? 'Cached ✓' : 'Success ✓');
                    updateMeta(bankId, data);
                    updateResponse(bankId, data);
                } else {
                    updateStatus(bankId, 'error', 'Error ✗');
                    updateMeta(bankId, null);
                    updateResponse(bankId, data);
                }
            } catch (error) {
                updateStatus(bankId, 'error', 'Error ✗');
                updateMeta(bankId, null);
                updateResponse(bankId, { error: error.message });
            } finally {
                setLoading(bankId, false);
            }
        }

        async function refreshBank(bankId) {
            updateStatus(bankId, 'loading', 'Refreshing...');
            setLoading(bankId, true);

            try {
                const response = await fetch(`/api/rates/refresh?bank=${bankId}`);
                const data = await response.json();

                if (response.ok) {
                    updateStatus(bankId, 'success', 'Success ✓');
                    updateMeta(bankId, data);
                    updateResponse(bankId, data);
                } else {
                    updateStatus(bankId, 'error', 'Error ✗');
                    updateMeta(bankId, null);
                    updateResponse(bankId, data);
                }
            } catch (error) {
                updateStatus(bankId, 'error', 'Error ✗');
                updateMeta(bankId, null);
                updateResponse(bankId, { error: error.message });
            } finally {
                setLoading(bankId, false);
            }
        }

        async function fetchAllBanks() {
            const btnText = document.getElementById('btn-text-all');
            const btn = document.getElementById('btn-all');
            const responseEl = document.getElementById('response-all');

            btnText.innerHTML = '<span class="loading-spinner"></span>';
            btn.disabled = true;

            try {
                const response = await fetch('/api/rates');
                const data = await response.json();

                if (response.ok) {
                    responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;

                    // Update individual bank cards
                    if (data.banks) {
                        for (const [bankId, bankData] of Object.entries(data.banks)) {
                            if (!bankData.error) {
                                updateStatus(bankId, bankData.cached ? 'cached' : 'success',
                                    bankData.cached ? 'Cached ✓' : 'Success ✓');
                                updateMeta(bankId, bankData);
                                updateResponse(bankId, bankData);
                            }
                        }
                    }
                } else {
                    responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                }
            } catch (error) {
                responseEl.innerHTML = `<pre>${JSON.stringify({ error: error.message }, null, 2)}</pre>`;
            } finally {
                btnText.textContent = 'Fetch All Banks';
                btn.disabled = false;
            }
        }

        async function refreshAllBanks() {
            const btnText = document.getElementById('btn-text-all');
            const btn = document.getElementById('btn-all');
            const responseEl = document.getElementById('response-all');

            btnText.innerHTML = '<span class="loading-spinner"></span>';
            btn.disabled = true;

            // Set all banks to loading
            ['landsbankinn', 'arionbanki', 'islandsbanki'].forEach(bankId => {
                updateStatus(bankId, 'loading', 'Refreshing...');
            });

            try {
                const response = await fetch('/api/rates/refresh');
                const data = await response.json();

                if (response.ok) {
                    responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;

                    // Update individual bank cards
                    if (data.banks) {
                        for (const [bankId, bankData] of Object.entries(data.banks)) {
                            if (!bankData.error) {
                                updateStatus(bankId, 'success', 'Success ✓');
                                updateMeta(bankId, bankData);
                                updateResponse(bankId, bankData);
                            } else {
                                updateStatus(bankId, 'error', 'Error ✗');
                            }
                        }
                    }
                } else {
                    responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                }
            } catch (error) {
                responseEl.innerHTML = `<pre>${JSON.stringify({ error: error.message }, null, 2)}</pre>`;
            } finally {
                btnText.textContent = 'Fetch All Banks';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""
