# Travel Recommendation Agent

You type in a trip, it gives you back flight info, real weather, safety
notes, and a day-by-day itinerary. Built with the raw Anthropic SDK, no
LangChain, mostly because I wanted to actually understand what's going on
under the hood instead of letting a framework do it for me.

## Example

You: "I'm flying to Lisbon for a long weekend next month."

It gives you:
```
Flight info: airline not specified, dates inferred as next month
Weather info: Lisbon is currently 23.6°C, pleasant temperatures expected...
Safety info: Lisbon is one of the safest capital cities in Europe...
Itinerary:
  - Day 1: Arrive, explore Alfama, dinner with fado music....
  - Day 2: Belém - Jerónimos Monastery, Belém Tower....
  - Day 3: Day trip to Sintra....
  - Day 4: Baixa, Chiado, Tram 28, fly home....
```

## How it actually works

1. Pull the flight details out of whatever you typed (structured output, no manual JSON parsing)
2. Get real coordinates, then hit the Open-Meteo API for the actual current temperature
3. Check `kb.json` for safety notes on the destination — if it's not in there, fall back to the model just knowing things
4. Generate the itinerary

## Running it

```
python3 -m venv venv
source venv/bin/activate
pip install anthropic pydantic python-dotenv requests
```

Drop your key in a `.env` file: `ANTHROPIC_API_KEY=your_key_here`

Then just:
```
python another_scratch_file.py
```

There's also a small eval script (`test_travel_agent.py`) — 19/22 checks passing right now.

## Stuff that's not perfect yet

- The gate check sometimes blocks real requests just because they're short on detail (a 5-day Tokyo trip scored 0.55 and got rejected, threshold is 0.6)
- If you mention two countries in one trip, it kind of just picks one and centers everything on that
- `kb.json` only has 15 destinations and I made up the numbers in it, so don't take the costs too seriously
