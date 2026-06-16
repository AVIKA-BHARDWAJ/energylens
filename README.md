# ⚡ EnergyLens — Energy Waste & Cost Audit Tool

**Live app:** https://energylens-f5tzrx29shgmrapkwjaxsl.streamlit.app/
**Author:** Avika Bhardwaj

## The Problem

Small businesses — shops, workshops, small manufacturing units — increasingly
have smart meters or inverter systems that log hourly energy usage. But that
data almost always just sits unused on a memory card or in a portal export.
There's no free, simple way for a small business owner to turn raw meter
readings into a clear answer to: *"When am I wasting energy, and what is it
costing me?"*

Existing tools either require expensive industrial energy-management
software, or only show a single bill total with no breakdown of *when* and
*why* usage spikes.

## What It Does

1. **Upload** a CSV with a timestamp column and an energy/kWh column (or use
   the built-in sample dataset simulating a small manufacturing unit).
2. The app **cleans and validates** the data — handling missing timestamps,
   non-numeric values, and negative readings (sensor errors), and tells you
   exactly what was dropped and why.
3. It computes:
   - Weekday vs weekend average usage
   - Peak demand hour
   - Total energy cost and estimated CO₂ emissions (using India's grid
     emission factor)
   - Share of usage happening during peak tariff hours
4. It gives a **plain-language recommendation**: how much you could save by
   shifting a portion of peak-hour load to off-peak hours.

## How It Was Built

- **Frontend/app framework:** Streamlit (chosen for fast deployment with no
  separate backend needed)
- **Data processing:** Pandas, NumPy — same workflow used in my [[Industrial
  Energy Consumption Analysis project](https://github.com/AVIKA-BHARDWAJ/industrial-energy-consumption-analysis)](#) (steel plant time-series analysis),
  generalized so it works on *any* uploaded dataset, not just one fixed file
- **Visualization:** Plotly (interactive charts inside Streamlit)
- **Assumptions documented in-app:** grid emission factor (CEA India, ~0.716
  kg CO₂/kWh), peak hour definition (commercial ToD tariff slabs), and the
  20% shiftable-load assumption used for savings estimates — all flagged
  to the user rather than hidden

## What Broke / What I Learned

- Initial `pd.date_range(freq="H")` failed on newer pandas — frequency
  strings changed to lowercase (`"h"`). Small thing, but a reminder to check
  library versions when generating test data.
- Real-world CSVs almost never have clean column names. Built a flexible
  column-matching system (checks for `timestamp`/`date`/`datetime` and
  `energy`/`kwh`/`usage`/`consumption` variants) instead of assuming exact
  names — otherwise the app would reject most real files.
- Originally assumed all uploaded data would have positive, valid readings.
  Added explicit dropping of negative values and non-numeric rows with a
  visible cleaning report, because silently failing or crashing on bad data
  would make the tool unusable for a non-technical small business owner.
- Learned that "shifting load" and "reducing emissions" are NOT the same
  thing — shifting only saves cost (via time-of-day tariffs), while cutting
  total CO₂ requires reducing total consumption. Made sure the
  recommendations section doesn't conflate the two.

## Run It Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tech Stack

Python · Pandas · NumPy · Streamlit · Plotly

<img width="1916" height="976" alt="image" src="https://github.com/user-attachments/assets/d7cc5d9f-807d-4359-b549-902da5a2f561" />
<img width="1917" height="982" alt="image" src="https://github.com/user-attachments/assets/2edacb9f-63c9-45ea-b7ea-d7ceee1921ba" />
<img width="1918" height="977" alt="image" src="https://github.com/user-attachments/assets/5271d886-483a-440e-b1d4-5e1a2f7a5ba2" />



