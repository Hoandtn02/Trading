"""
Bond Analyzer Module - Final Phase
Phân tích trái phiếu chính phủ và doanh nghiệp
"""
from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
from datetime import datetime


@dataclass
class BondData:
    """Data structure for bond information"""
    symbol: str = ""
    name: str = ""
    bond_type: str = ""  # "government", "corporate"
    face_value: float = 0.0  # Mệnh giá
    current_price: float = 0.0
    coupon_rate: float = 0.0  # Lãi suất coupon (%/năm)
    yield_to_maturity: float = 0.0  # Lợi suất đáo hạn
    maturity_date: str = ""
    days_to_maturity: int = 0
    duration: float = 0.0
    modified_duration: float = 0.0
    change_percent: float = 0.0
    volume: float = 0.0
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class BondAnalyzer:
    """Analyzer for bonds (government and corporate)"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "bond_default") -> BondData:
        """
        Analyze bond
        
        Args:
            symbol: Bond symbol or "gov_bonds" for government bonds list
        """
        data = BondData(symbol=symbol, name=self._get_name(symbol))
        
        if symbol.lower() in ["gov_bonds", "government", "list"]:
            self._get_government_bonds(data)
        else:
            self._get_bond_data(data)
        
        self._determine_status(data)
        
        return data
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "gov_bonds": "Trái phiếu Chính phủ",
            "government": "Trái phiếu Chính phủ",
            "corporate": "Trái phiếu Doanh nghiệp",
        }
        return names.get(symbol, f"Trái phiếu {symbol}")
    
    def _get_government_bonds(self, data: BondData):
        """Get government bonds listing"""
        data.bond_type = "government"
        
        try:
            from vnstock_data import Reference
            
            ref = Reference()
            bonds = ref.bond.list()
            
            if bonds is not None and len(bonds) > 0:
                data.bonds_list = bonds
            else:
                # Fallback to listing API
                from vnstock.explorer.vci.listing import Listing
                listing = Listing(show_log=False)
                bonds = listing.all_government_bonds()
                
                if bonds is not None and hasattr(bonds, 'head'):
                    data.bonds_list = bonds.head(10)
                    
        except Exception as e:
            print(f"[BondAnalyzer] Government bonds error: {e}")
    
    def _get_bond_data(self, data: BondData):
        """Get specific bond data"""
        try:
            from vnstock_data import Reference
            
            ref = Reference()
            bond_info = ref.bond.list()
            
            # Find the bond in list
            if bond_info is not None and len(bond_info) > 0:
                if hasattr(bond_info, 'columns'):
                    if 'symbol' in bond_info.columns:
                        bond_row = bond_info[bond_info['symbol'] == data.symbol]
                        if len(bond_row) > 0:
                            row = bond_row.iloc[0]
                            data.coupon_rate = float(row.get('coupon_rate', 0))
                            data.face_value = float(row.get('face_value', 100000))
                            data.maturity_date = str(row.get('maturity_date', ''))
            
            # Try to get price from market
            try:
                from vnstock_data import Market
                mkt = Market()
                
                # Government bonds might be in a different format
                df = mkt.bond(data.symbol).history(length=f"{self.period_ta}D")
                
                if df is not None and len(df) > 0:
                    last = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else last
                    
                    for col in df.columns:
                        if 'close' in col.lower():
                            data.current_price = float(last.get(col, 0))
                            prev_price = float(prev.get(col, data.current_price))
                            
                            if prev_price > 0:
                                data.change_percent = round((data.current_price - prev_price) / prev_price * 100, 2)
                            break
                    else:
                        # Default: use last column
                        data.current_price = float(last.iloc[-1])
                        
            except Exception as e:
                # If no price data, use face value
                data.current_price = data.face_value
                print(f"[BondAnalyzer] Bond price error: {e}")
                
        except Exception as e:
            print(f"[BondAnalyzer] Error: {e}")
    
    def _calculate_yield(self, data: BondData):
        """Calculate yield to maturity (simplified)"""
        try:
            if data.coupon_rate > 0 and data.days_to_maturity > 0:
                years_to_maturity = data.days_to_maturity / 365
                
                # Simplified YTM calculation
                # YTM ≈ (C + (F - P) / n) / ((F + P) / 2)
                # Where C = coupon, F = face value, P = price, n = years
                
                coupon = data.coupon_rate * data.face_value / 100
                price_diff = data.face_value - data.current_price
                
                avg_price = (data.face_value + data.current_price) / 2
                
                if avg_price > 0:
                    data.yield_to_maturity = round(
                        (coupon + price_diff / years_to_maturity) / avg_price * 100, 2
                    )
                    
        except Exception as e:
            print(f"[BondAnalyzer] YTM calculation error: {e}")
    
    def _determine_status(self, data: BondData):
        """Determine bond status"""
        # Yield trend
        if data.yield_to_maturity > 0:
            if data.yield_to_maturity > 7:
                data.trend = "HIGH YIELD"
            elif data.yield_to_maturity > 5:
                data.trend = "MEDIUM YIELD"
            else:
                data.trend = "LOW YIELD"
        
        # Duration risk
        if data.days_to_maturity > 0:
            years = data.days_to_maturity / 365
            if years > 10:
                data.trend += " (Long-term)"
            elif years > 5:
                data.trend += " (Medium-term)"
            else:
                data.trend += " (Short-term)"
        
        # Status
        if data.change_percent >= 0.1:
            data.technical_status = "BULLISH"
        elif data.change_percent <= -0.1:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def get_government_bonds_list(self) -> pd.DataFrame:
        """Get list of government bonds"""
        try:
            from vnstock.explorer.vci.listing import Listing
            listing = Listing(show_log=False)
            bonds = listing.all_government_bonds()
            
            if bonds is not None:
                if hasattr(bonds, 'to_frame'):
                    return bonds.to_frame()
                return bonds
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"[BondAnalyzer] List error: {e}")
            return pd.DataFrame()
    
    def format_output(self, data: BondData) -> str:
        """Format analysis output"""
        trend_emoji = "📈" if data.technical_status == "BULLISH" else "📉" if data.technical_status == "BEARISH" else "➡️"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 BOND ANALYSIS: {data.name}
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  🏦 LOẠI: {data.bond_type.upper()}
║  💰 MỆNH GIÁ: {data.face_value:,.0f} VND
║  💵 GIÁ HIỆN TẠI: {data.current_price:,.0f} VND
║  {trend_emoji} Thay đổi: {data.change_percent:+.2f}%
╠══════════════════════════════════════════════════════════════╣
║  📋 CHI TIẾT:
║     Lãi suất Coupon: {data.coupon_rate:.2f}%/năm
║     Lợi suất YTM: {data.yield_to_maturity:.2f}%
║     Ngày đáo hạn: {data.maturity_date}
║     Số ngày đến đáo hạn: {data.days_to_maturity}
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  📊 TÌNH TRẠNG: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: BondData) -> str:
        """Get investment recommendation"""
        score = 50
        
        # Yield scoring
        if data.yield_to_maturity > 7:
            score += 10
        elif data.yield_to_maturity < 4:
            score -= 10
        
        # Duration risk
        if data.days_to_maturity > 3650:  # > 10 years
            score -= 5  # Long duration = higher risk
        
        # Price change
        if data.change_percent > 0.5:
            score += 5
        elif data.change_percent < -0.5:
            score -= 5
        
        if score >= 60:
            return "TÍCH CỰC - Có thể mua"
        elif score >= 40:
            return "TRUNG LẬP - Chờ xác nhận"
        else:
            return "THẬN TRỌNG - Xem xét kỹ"


# Government Bond Indices
class GovBondIndexAnalyzer:
    """Analyzer for government bond indices"""

    def __init__(self):
        self.indices = {
            "VNBY1Y": "Trái phiếu CP 1 năm",
            "VNBY3Y": "Trái phiếu CP 3 năm",
            "VNBY5Y": "Trái phiếu CP 5 năm",
            "VNBY10Y": "Trái phiếu CP 10 năm",
        }

    def run(self, symbol: str = "VNBY5Y") -> BondData:
        """Main entry point - compatible with runner interface"""
        return self._analyze_bond_index(symbol)

    def _analyze_bond_index(self, symbol: str = "VNBY5Y") -> BondData:
        """Analyze a government bond index"""
        name = self.indices.get(symbol, symbol)

        data = BondData(
            symbol=symbol,
            name=name,
            bond_type='government'
        )

        try:
            # Try to get bond index data from vnstock_data
            from vnstock_data import Market
            mkt = Market()

            df = mkt.bond(symbol).history(length="30D")

            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last

                # Find close column
                value = 0.0
                prev_value = 0.0
                for col in df.columns:
                    if 'close' in col.lower():
                        value = float(last.get(col, 0))
                        prev_value = float(prev.get(col, 0))
                        break

                if value == 0 and len(df.columns) > 0:
                    value = float(last.iloc[-1])
                    prev_value = float(prev.iloc[-1])

                data.current_price = value
                change = value - prev_value
                if prev_value > 0:
                    data.change_percent = round(change / prev_value * 100, 2)

                if data.change_percent > 0:
                    data.trend = "UPTREND"
                elif data.change_percent < 0:
                    data.trend = "DOWNTREND"
                else:
                    data.trend = "SIDEWAYS"
            else:
                # Fallback: use default values
                data.current_price = 100.0
                data.trend = "NEUTRAL"

        except Exception as e:
            print(f"[GovBondIndexAnalyzer] Error: {e}")
            data.current_price = 100.0
            data.trend = "NEUTRAL"

        return data

    def analyze(self, symbol: str = "VNBY5Y") -> BondData:
        """Analyze a government bond index - alias for run()"""
        return self.run(symbol)

    def format_output(self, data: BondData) -> str:
        """Format bond analysis output"""
        trend_color = "🟢" if data.trend == "UPTREND" else "🔴" if data.trend == "DOWNTREND" else "🟡"
        return f"""
╔══════════════════════════════════════════════════════════════╗
║  🏦 TRAI PHIEU CHINH PHU
║  Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  Chi so: {data.name}
║  Gia: {data.current_price:,.2f}
║  {trend_color} Thay doi: {data.change_percent:+.2f}%
║  Xu huong: {data.trend}
╚══════════════════════════════════════════════════════════════╝
"""
