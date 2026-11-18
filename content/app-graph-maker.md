<!--
  Help text for the Graph Maker tab (public page and configurator).
  Normal Markdown. Screenshots live in content/images/ and are written as ![description](images/file.png).
  Change the app's address in content/apps.json, not here.
-->
## Graph Maker

Graph Maker builds chart graphics for on-air weather segments and exports them as transparent PNGs you drop into Max. You can type or paste your own numbers, or pull a station's full daily history from ACIS, the official NWS source (the data behind xmACIS), and let the app work out records, normals and rankings for you.

![The Year Ranking chart type with the station data panel for Columbus, Ohio](images/graph-maker-station-data.png)
*Year Ranking selected: choose a state, station, variable and period, then click Use this station data.*

### What it can do

- **Your own data.** Type into the table, paste cells straight from Excel or Google Sheets (xmACIS and NOWData work too), or import a CSV or Excel file. The first column is the labels, the next one or two columns are the numbers.
- **Bar and line charts** with one or two series, a highlighted point, and optional data labels. Bars can run vertically or horizontally, which suits sorted top-10 lists and named rows.
- **Four climate presets** (marked with a star) that pull a station's daily record from ACIS:
    - **Running Total:** season-to-date rain or snow against normal, with the range of all years and the highest and lowest years. Pick when the season starts (snow seasons usually start Jul 1, water years Oct 1, or a meteorological season) and whether to show the normal for the rest of the season.
    - **Climo Band:** each day's highs and lows over the record-high band, the normal range and the record-low band, for a full year, a month, a date range or a single year, with new records marked.
    - **Year Ranking:** every year on record, by year or sorted, with one year highlighted and ranked ("5th wettest of 133 years"), an average line and an optional trend line. Years missing more than a set number of days are left out.
    - **Range Bars:** floating bars from a start to an end, such as the growing season for every year (the last spring and first fall low at or below 32 degrees by default; use 28 for a hard freeze).
- **Import from an IEM autoplot.** Paste the address of a plot made at mesonet.agron.iastate.edu/plotting/auto, then pick which of its columns go into the chart. Not every autoplot offers its data.
- **Number formatting.** Decimal places, prefixes and suffixes such as a degree sign or percent, and thousands separators.
- **Look.** Size, fonts, colors, gridlines, axis interval and label rotation. Colors come from the Weather Impact 2.0 palette, picked by clicking color chips.
- **Projects.** Save your data and settings as a JSON file and load it again later.
- **No titles or legends.** Those are added in Max.

### How to use it

1. Open the app (button at the top of this tab).
2. Pick a **Chart Type** across the top.
3. Get your data in. Either fill the table, paste, or import; or, for a starred preset, choose a **State** and **Station**, set that preset's options (for Year Ranking a **Variable** and **Period**; Running Total a **Season starts**; Climo Band a **Period**), and click **Use this station data**. "Area" stations are a city's long-term threaded record.
4. Adjust the look in the sidebar: canvas size, preset options such as the highlighted year, colors, data labels, axes and gridlines. The chart updates as you go.
5. Download the chart as a transparent PNG and place it in Max.
6. To keep working later, save the project file and load it next time.

![Year Ranking for Columbus, Ohio: every year of year-to-date precipitation, with the latest year highlighted and an average line](images/graph-maker-year-ranking.png)
*Year Ranking: every year's year-to-date precipitation at the Columbus Area station, the latest year in light blue and the average as a navy line.*

![Running total of precipitation for the year against the range of all years and the normal](images/graph-maker-running-total.png)
*Running Total: this year (thick light blue) against the range of every year (tan), the highest and lowest years (thin lines) and the normal (dashed).*

![Climo Band for Columbus: daily highs and lows over the record-high, normal and record-low bands, with new records marked](images/graph-maker-climo-band.png)
*Climo Band: this year's daily highs and lows (blue) over the record-high (warm), normal (green) and record-low (cool) bands, with new records marked in yellow.*

### Where the numbers come from

- **Station data** comes from ACIS, the official NWS source, so records, normals and rankings use the same observations as xmACIS and NOWData. Each station shows the dates its daily data covers.
- **Normals** can be NCEI's official 1991-2020 normals (the default, the ones the NWS daily climate report uses) or averages over the station's full record. IEM's own plot (#113) uses full-record averages, so pick **Full record** if you want to match it.
- **Your own numbers** can still be pasted or imported from xmACIS, NOWData or any other source. The table accepts T (trace) and M (missing).
- **Dates as values** (for example the last spring freeze per year, as `16-Oct` or `2025-10-16`) are read as dates, shown as "Oct 16", ranked as latest or earliest, and any trend line is labeled in days per decade.
- The app runs on Streamlit Community Cloud, which puts idle apps to sleep. If you see a "wake up" message, click it and allow about 30 seconds, and open the app before you need it on air.
