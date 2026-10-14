import express from 'express';
import { getCandles, getIndicatorData, getQuote } from '@mathieuc/tradingview/data';

const app = express();
app.use(express.json());

// Your TradingView Credentials
const credentials = {
  session: '6o3p5vfbxr80jcj9zwl0nda3nh9x14zo',
  signature: 'v3:BVPDdJyiOc181M/Is/HTY21sFVpEUzDyNlavk6Olbss='
};

// Endpoint 1: Lấy OHLCV
app.get('/candles', async (req, res) => {
  const { symbol, timeframe = 'D', count = 250 } = req.query;
  try {
    const candles = await getCandles({ symbol, timeframe, count: parseInt(count) });
    res.json({ ok: true, data: candles });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// Endpoint 2: Lấy Indicators
app.post('/indicators', async (req, res) => {
  const { symbol, indicator, indicators, timeframe = 'D', inputs } = req.body;
  
  try {
    // Hỗ trợ lấy nhiều indicators cùng lúc để tối ưu tốc độ
    if (indicators && Array.isArray(indicators)) {
        const promises = indicators.map(ind => {
            const options = { symbol, indicator: ind, credentials };
            return getIndicatorData(options).then(res => ({
                indicator: ind,
                data: res.values
            })).catch(err => ({
                indicator: ind,
                error: err.message
            }));
        });
        const results = await Promise.all(promises);
        return res.json({ ok: true, data: results });
    }

    // Lấy 1 indicator đơn lẻ
    const options = { symbol, indicator, credentials };
    if (inputs) {
        options.inputs = inputs;
    }
    const result = await getIndicatorData(options);
    res.json({ ok: true, data: result.values });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// Endpoint 3: Quote real-time
app.get('/quote', async (req, res) => {
  const { symbol } = req.query;
  try {
    const q = await getQuote(symbol);
    res.json({ ok: true, data: q });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

const PORT = 7788;
app.listen(PORT, () => console.log(`TV Service running on :${PORT}`));
