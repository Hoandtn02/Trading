from django.db import models


class FunctionGroup(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class FunctionDefinition(models.Model):
    group = models.ForeignKey(FunctionGroup, on_delete=models.CASCADE, related_name="functions")
    function_id = models.CharField(max_length=120, unique=True)
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    runner_path = models.CharField(max_length=255)
    param_schema = models.JSONField(default=dict)
    output_type = models.CharField(max_length=50, default="table")
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.label


class ExecutionHistory(models.Model):
    function = models.ForeignKey(FunctionDefinition, on_delete=models.CASCADE, related_name="history")
    params = models.JSONField(default=dict)
    status = models.CharField(max_length=30, default="success")
    result_preview = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class UserPreset(models.Model):
    name = models.CharField(max_length=120)
    function = models.ForeignKey(FunctionDefinition, on_delete=models.CASCADE, related_name="presets")
    params = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class ExecutionResult(models.Model):
    function = models.ForeignKey(FunctionDefinition, on_delete=models.CASCADE, related_name="results")
    params = models.JSONField(default=dict)
    status = models.CharField(max_length=30, default="success")
    result_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


# ============== STOCK DATA MODELS (Database-First Architecture) ==============

class StockData(models.Model):
    """Lưu trữ dữ liệu kỹ thuật của mã cổ phiếu"""
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    company_name = models.CharField(max_length=200, blank=True, default="")

    # Price
    price = models.FloatField(default=0)
    change_percent = models.FloatField(default=0)
    volume = models.BigIntegerField(default=0)
    avg_volume_value = models.FloatField(default=0)  # Tỷ VND

    # Technical Indicators
    rsi = models.FloatField(default=50)
    adx = models.FloatField(default=25)
    plus_di = models.FloatField(default=0)
    minus_di = models.FloatField(default=0)
    cmf = models.FloatField(default=0)
    atr = models.FloatField(default=0)

    # Moving Averages
    sma_10 = models.FloatField(default=0)
    sma_20 = models.FloatField(default=0)
    sma_50 = models.FloatField(default=0)

    # Bollinger Bands
    bb_upper = models.FloatField(default=0)
    bb_middle = models.FloatField(default=0)
    bb_lower = models.FloatField(default=0)
    bb_percent = models.FloatField(default=50)

    # MACD
    macd = models.FloatField(default=0)
    macd_signal = models.FloatField(default=0)

    # Volume
    volume_ratio = models.FloatField(default=1.0)

    # Fundamental (optional, may be None)
    pe = models.FloatField(null=True, blank=True)
    pb = models.FloatField(null=True, blank=True)
    roe = models.FloatField(null=True, blank=True)

    # Meta
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_data"
        ordering = ["-avg_volume_value"]

    def __str__(self):
        return f"{self.symbol}: {self.price}"


class StockAnalysis(models.Model):
    """Lưu trữ kết quả phân tích AI của mã cổ phiếu"""
    symbol = models.OneToOneField(StockData, on_delete=models.CASCADE, related_name="analysis")

    # Scores
    master_score = models.IntegerField(default=50)
    technical_score = models.IntegerField(default=50)
    fundamental_score = models.IntegerField(default=50)

    # Signal
    signal = models.CharField(max_length=20, default="WAIT")  # BUY/SELL/WAIT/ACCUMULATE

    # Trading Levels
    entry_price = models.FloatField(default=0)
    stop_loss = models.FloatField(default=0)
    take_profit = models.FloatField(default=0)
    risk_reward_ratio = models.FloatField(default=0)

    # Status Flags
    is_vetoed = models.BooleanField(default=False)
    veto_reason = models.CharField(max_length=200, blank=True, default="")
    is_fast_pick = models.BooleanField(default=False)
    is_short_term_qualified = models.BooleanField(default=False)
    is_slow_mode = models.BooleanField(default=False)
    is_high_risk = models.BooleanField(default=False)
    has_inverted_sl = models.BooleanField(default=False)

    # Holding
    estimated_days_to_target = models.FloatField(default=0)

    # Criteria
    criteria_met = models.IntegerField(default=0)
    criteria_list = models.JSONField(default=list)

    # Trend
    trend = models.CharField(max_length=20, default="SIDEWAYS")
    breakout_status = models.CharField(max_length=50, default="")

    # Meta
    market_rsi = models.FloatField(default=50)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_analysis"
        ordering = ["-risk_reward_ratio", "-master_score"]

    def __str__(self):
        return f"{self.symbol}: {self.signal} (Score: {self.master_score})"


class SyncStatus(models.Model):
    """Theo dõi trạng thái đồng bộ"""
    STATUS_CHOICES = [
        ("idle", "Idle"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="idle")
    total_symbols = models.IntegerField(default=0)
    processed_symbols = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sync_status"

    @property
    def progress_percent(self):
        if self.total_symbols == 0:
            return 0
        return int(self.processed_symbols / self.total_symbols * 100)

    @property
    def is_running(self):
        return self.status == "running"
