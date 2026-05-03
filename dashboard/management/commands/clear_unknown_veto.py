"""
Management command: Clear veto flags for stocks that were incorrectly vetoed
due to UNKNOWN market_group before the VN30 fix.
"""
from django.core.management.base import BaseCommand
from dashboard.models import StockData


class Command(BaseCommand):
    help = "Clear veto flags for stocks that were incorrectly vetoed as 'Không thuộc VN30/MIDCAP (UNKNOWN)'"

    def handle(self, *args, **options):
        # Find all stocks with the old UNKNOWN veto reason
        vetoed_unknown = StockData.objects.filter(
            is_vetoed=True,
            veto_reason__contains='Không thuộc VN30/MIDCAP'
        )

        count = vetoed_unknown.count()
        self.stdout.write(f"Found {count} stocks incorrectly vetoed as UNKNOWN...")

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No stocks to fix."))
            return

        # Check which ones are actually VN30
        try:
            from vnstock_data import Reference
            ref = Reference()
            vn30_list = list(ref.equity.list_by_group(group="VN30")['symbol'].str.upper())
            self.stdout.write(f"VN30 list loaded: {len(vn30_list)} symbols")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not fetch VN30 list: {e}"))
            vn30_list = list(StockData.objects.filter(market_group='VN30').values_list('symbol', flat=True))

        cleared = 0
        for stock in vetoed_unknown:
            symbol = stock.symbol.upper()
            in_vn30 = symbol in vn30_list
            # If it's VN30, set market_group and clear veto
            if in_vn30 and stock.market_group != 'VN30':
                stock.market_group = 'VN30'
                stock.save(update_fields=['market_group'])
                self.stdout.write(f"  Updated {symbol} -> VN30")
            # Clear veto
            stock.is_vetoed = False
            stock.veto_reason = ''
            stock.save(update_fields=['is_vetoed', 'veto_reason'])
            cleared += 1
            self.stdout.write(f"  Cleared veto: {symbol} (was: {stock.veto_reason})")

        self.stdout.write(self.style.SUCCESS(f"Done. Cleared {cleared} veto flags."))
