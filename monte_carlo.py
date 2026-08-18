import numpy as np

rng = np.random.default_rng(42)
N = 10000

# --- Sampled variables per the proposed distributions ---
co2_pct = rng.triangular(0.18, 0.20, 0.22, N)                      # baseline flue gas CO2% (Hope, cement-only, tightened range)
o2_ratio = np.clip(rng.normal(0.30, 0.04, N), 0.20, 0.40)           # t O2 / t CO2
retrofit_capex_tpa = rng.uniform(30, 80, N)                         # £/tpa CO2 capacity
grid_offset = rng.uniform(0, 5_000_000, N)                          # £
tariff = np.clip(rng.normal(105, 15, N), 85, 140)                   # £/MWh (DESNZ/Ofgem-informed range)

# --- Fixed model defaults (unchanged from the verified spreadsheet) ---
VOL = 1_200_000        # Hope Cement Works (Hope Valley Climate Action: ~1.2Mt CO2/yr)
CO2_REF = 0.20
AMINE_THERMAL = 900.0        # kWh-th/t at reference
THERMAL_COST = 35.0          # £/MWh-th
AMINE_ELEC = 40.0
COMPR = 105.0
AMINE_CAPEX_TPA = 320.0
AMINE_OPEX_T = 8.0
ASU_SPEC = 300.0              # kWh/t O2 (NOT sampled here, per the 5-variable spec)
ASU_CAPEX_TPA = 160.0
PURIF = 30.0
OXY_OPEX_T = 5.0
KILN_MW = 140.0         # calculated estimate — see notebook for derivation, not a confirmed nameplate figure
WHR_FRAC = 0.35
ORC_EFF = 0.18
ORC_CAPEX_MWE = 2_000_000.0
HOURS = 8000.0
BESS_CAPEX_KWH = 280.0
BESS_MW = 10.0
BESS_HRS = 4.0
DISC = 0.08
LIFE = 20

CRF = (DISC * (1 + DISC) ** LIFE) / ((1 + DISC) ** LIFE - 1)

# --- Baseline (amine) ---
reboiler_kwh_t = AMINE_THERMAL * (CO2_REF / co2_pct)
thermal_cost_t = reboiler_kwh_t * THERMAL_COST / 1000
elec_kwh_t = AMINE_ELEC + COMPR
elec_cost_t = elec_kwh_t * tariff / 1000
base_opex_t = thermal_cost_t + elec_cost_t + AMINE_OPEX_T
base_capex = AMINE_CAPEX_TPA * VOL
base_lev_capex_t = (base_capex * CRF) / VOL
base_allin = base_opex_t + base_lev_capex_t

# --- Optimized (oxy-fuel + WHR + BESS) ---
o2_t = o2_ratio * VOL
asu_kwh_t = o2_ratio * ASU_SPEC
total_kwh_t = asu_kwh_t + PURIF + COMPR
total_mwh = total_kwh_t * VOL / 1000

heat_mw = KILN_MW * WHR_FRAC
orc_mw = heat_mw * ORC_EFF
whr_mwh = orc_mw * HOURS

netgrid_mwh = np.maximum(0, total_mwh - whr_mwh)
grid_cost = netgrid_mwh * tariff
nonenergy = OXY_OPEX_T * VOL
opt_opex_t = (grid_cost + nonenergy) / VOL

asu_capex = ASU_CAPEX_TPA * o2_t
retrofit_capex = retrofit_capex_tpa * VOL
orc_capex = orc_mw * ORC_CAPEX_MWE
bess_capex = BESS_MW * BESS_HRS * 1000 * BESS_CAPEX_KWH
capex_gross = asu_capex + retrofit_capex + orc_capex + bess_capex
capex_net = capex_gross - grid_offset
opt_lev_capex_t = (capex_net * CRF) / VOL
opt_allin = opt_opex_t + opt_lev_capex_t

savings = base_allin - opt_allin

p10, p50, p90 = np.percentile(savings, [10, 50, 90])
win_rate = (savings > 0).mean()

print(f"P10 (worst 10%)  : £{p10:.2f} / t")
print(f"P50 (median)     : £{p50:.2f} / t")
print(f"P90 (best case)  : £{p90:.2f} / t")
print(f"Min observed     : £{savings.min():.2f} / t")
print(f"Max observed     : £{savings.max():.2f} / t")
print(f"Win rate (optimized cheaper): {win_rate*100:.2f}%  ({(savings>0).sum()} / {N})")
print(f"Mean: £{savings.mean():.2f} / t   SD: £{savings.std():.2f} / t")

# What does the worst-case tail actually look like?
worst_idx = np.argsort(savings)[:5]
print("\n5 worst-case draws (lowest savings):")
for i in worst_idx:
    print(f"  savings=£{savings[i]:.2f}  co2%={co2_pct[i]:.3f}  o2_ratio={o2_ratio[i]:.3f}  "
          f"retrofit=£{retrofit_capex_tpa[i]:.1f}/tpa  grid_offset=£{grid_offset[i]:,.0f}  tariff=£{tariff[i]:.1f}")
