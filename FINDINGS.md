# What the data says

Six years of Australia's National Electricity Market, five-minute by five-minute: price and
demand from June 2020, and the output of every utility-scale generator from mid-2024. All of
it is AEMO's public data, and every number below can be rebuilt from the dbt models in this
repo. Two caveats apply to everything: generation excludes rooftop solar (the market counts
it as demand that never showed up), and carbon intensity is estimated from standard
emission factors per fuel, not measured.

## The transition is real, and it is uneven

Renewables supply about a third of utility-scale generation nationally, up from a little
under a third at the start of the generation data, and the line only ever moves one way
once you look through the seasons.

The national figure hides most of the story. Tasmania has always run on hydro and sits near
100%. South Australia has rebuilt itself around wind and solar and now runs on them roughly
three-quarters of the time. The three coal states are bunched together around a third, and
of those, Queensland is moving fastest — up nearly eight points in eighteen months as
utility-scale solar came online.

## The clearest signal is a price below zero

On a sunny, windy afternoon there is more renewable power than the grid can absorb, and
because it costs nothing to produce, the price does not stop at zero. Generators end up
paying to stay connected.

Across six years, **13.7% of all five-minute intervals cleared below $0** — about one in
seven. It rose from 5% of intervals in 2020 to 18% in 2025. Some of the early jump is a
change in how the market settles (30-minute to 5-minute, in October 2021), but from 2021
on the comparison is like-for-like and the rise is real.

In 2025, South Australia was below zero 30% of the time. Victoria 24%, Queensland 20%,
New South Wales 14%, Tasmania 3%. Line the states up by renewable share and you get the
same order. Nobody designed that; it is what a grid does when weather becomes supply.

## Victoria has the dirtiest power in the country

Carbon intensity follows the fuel almost exactly. Brown coal emits about a third more
carbon per unit of power than black coal, and Victoria runs on brown coal, so it sits
around **776 kg of CO₂ per megawatt-hour**. New South Wales and Queensland, on black coal,
are around 605. South Australia is about 115. Tasmania is effectively zero.

Nationally the figure eased from about 607 to about 590 over the period — a small move,
because the coal fleet is still doing most of the work. The point is not that it moved
much; it is that it will keep moving in the same direction as long as the chart above does.

## 2022 was the biggest event in the data, and nobody had to point it out

Monthly average prices spiked to around **$400 a megawatt-hour in mid-2022**. A run of
coal-plant breakdowns met a global gas shortage, prices went so high that the market
operator suspended trading for a fortnight, and every state got dragged up together. It
dwarfs everything else on the chart.

The market has hard bounds — a floor of −$1,000, and a cap that AEMO raises every July.
The cap has climbed relentlessly: $10,034 in 2020, then $15,100, $16,600, $17,500,
$20,300, and **$23,200 from July 2026**. That last figure is not theoretical. Tasmania
cleared at exactly $23,200 on 13 July 2026 at 4:20 in the afternoon, a fortnight after
the new cap took effect.

## Demand is forecastable, mostly

A model predicting seven days of demand per state lands within about **3% in New South
Wales and Queensland**, and about **7% in South Australia**. The gap is not a failure of
the model; a grid that runs on weather is harder to predict than one that runs on coal.
The transition shows up in the error bars too.

I tested it the honest way — hiding six separate weeks of history and scoring the guesses
— and both models I kept beat the obvious baseline of *assume next week looks like last
week*, by 16 to 31 percent depending on the state.

## The database can forecast too, and sometimes better

Snowflake can run forecasting from plain SQL, so I gave it the same problem: same six
years of history, same hidden week, same scoring. It came out **ahead on average — 3.3%
error against 4.0%** for the best Python model — and it was much better in South
Australia, where it roughly halved the error. It lost in New South Wales and Queensland,
the two biggest and steadiest states. A single hidden week is 35 predictions, which is
enough to be interesting and not enough to declare a winner.

Its anomaly detection was the more convincing half. Trained on 2020–2024 prices, it
flagged 54 of 2,585 recent state-days as unusual. The two that stand out are real events:
South Australia clearing $2,457 against an expected $75 on 26 January 2026, a public
holiday in a heatwave; and 12 and 26 June 2025 flagged in Victoria, South Australia and
Tasmania on the same evenings — winter cold-snap peaks across the whole southern grid,
which the model found without being told the three were connected.

## Two things that only broke in the cloud

The first cloud run failed a data test, and the test was right. I had bounded price at
$21,000 because the market has a regulated cap and anything above it means my parsing
broke. Then AEMO raised the cap on 1 July and Tasmania hit it. My laptop had never seen
July. The bound now sits at $40,000 — high enough to catch a ten-times scaling fault,
which would read about $232,000, and no longer pretending to track a number that moves
every year.

The second was stranger. All twenty-four monthly generation files returned 404 in the
cloud and downloaded fine on my Mac. It was not an IP block; the directory listings
worked from both places. The filenames contain a literal `#`, and NEMWEB percent-encodes
it differently depending on which edge of its CDN answers you — `%2523` from Sydney,
`%23` from a runner in Arizona — and each rejects the other. There is no correct value to
hardcode, so the fix reads the link out of the directory listing instead. Three months I
had written off as "not yet published" turned out to be the same bug.

---

Data © AEMO, used for non-commercial, educational purposes.
