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
