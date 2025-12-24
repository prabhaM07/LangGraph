from typing import Dict, List
from travelState import TravelState
import ast


def content_correction(content: str) -> str:
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    return content


def generate_final_result(state: TravelState) -> Dict:
    """Generate final recommendations from available data, including weather"""

    recommendations: List[Dict] = []
    sources_used: List[str] = []

    for source_name, extractor in [
        ("pdf", _extract_from_pdf),
        ("database", _extract_from_database),
        ("web_search", _extract_from_web),
    ]:
        results = extractor(state)
        if results:
            recommendations.extend(results)
            sources_used.append(source_name)

    weather_info = _extract_weather(state)
    if weather_info:
        sources_used.append("weather")

    # Weather-only response
    if not recommendations and weather_info:
        destination_name = weather_info.get("destination", "the destination")
        summary = (
            f"Weather for {destination_name}: "
            f"{weather_info.get('temperature_range', 'N/A')} | "
            f"{weather_info.get('conditions', 'N/A')}"
        )

        return {
            "recommendations": [],
            "summary": summary,
            "total_found": 0,
            "data_source": "weather",
            "weather_info": weather_info,
            "weather_only": True,
        }

    recommendations = _deduplicate(recommendations)
    recommendations = _rank(
        recommendations,
        state.get("user_preferences").model_dump(),
    )

    if weather_info:
        recommendations = _add_weather_to_recommendations(
            recommendations, weather_info
        )

    if recommendations:
        top = recommendations[0]
        summary_parts = [f"Top destination: {top['destination']}"]

        if top.get("cost") not in (None, "N/A"):
            summary_parts.append(f"Cost: ₹{top['cost']}")

        if weather_info:
            summary_parts.append(weather_info.get("temperature_range", ""))

        summary = " | ".join(summary_parts)
    else:
        summary = "No recommendations found"

    return {
        "recommendations": recommendations[:10],
        "summary": summary,
        "total_found": len(recommendations),
        "data_source": "+".join(sources_used) or "none",
        "weather_info": weather_info,
    }


def _extract_from_pdf(state: TravelState) -> List[Dict]:
    packages = state.get("extracted_data", {}).get("packages", [])

    return [
        {
            "destination": p.get("destination", "Unknown"),
            "country": p.get("country", "N/A"),
            "cost": p.get("price") or p.get("budget_max", "N/A"),
            "activities": ", ".join(p.get("activities", [])),
            "best_season": p.get("best_season")
            or p.get("travel_month", "N/A"),
            "description": p.get("description", ""),
            "source": "PDF",
        }
        for p in packages[:10]
    ]


def _extract_from_database(state: TravelState) -> List[Dict]:
    db_results = state.get("db_results", {})

    if not db_results.get("success"):
        return []

    destinations = db_results.get("destinations", "")
    if not destinations or not destinations.strip().startswith("["):
        return []

    try:
        db_tuples = ast.literal_eval(destinations)
        results = []

        for budget_max, activities, travel_month, states, countries in db_tuples:
            destination = (
                states[0]
                if states
                else countries[0]
                if countries
                else None
            )
            if not destination:
                continue

            results.append(
                {
                    "destination": destination,
                    "country": countries[0] if countries else "N/A",
                    "cost": budget_max,
                    "activities": ", ".join(activities)
                    if activities
                    else "Various",
                    "best_season": travel_month or "N/A",
                    "description": (
                        f"Features {', '.join(activities[:2])}"
                        if activities
                        else ""
                    ),
                    "source": "Database",
                }
            )

        return results
    except Exception:
        return []


def _extract_from_web(state: TravelState) -> List[Dict]:
    web_results = state.get("web_results", {})

    if not web_results.get("success"):
        return []

    destinations = web_results.get("destinations", [])

    if isinstance(destinations, str):
        try:
            import json

            destinations = json.loads(destinations).get("destinations", [])
        except Exception:
            return []

    return [
        {
            "destination": d.get("name", "Unknown"),
            "country": d.get("country", "N/A"),
            "cost": d.get("estimated_cost", "N/A"),
            "activities": ", ".join(d.get("activities", [])),
            "best_season": d.get("best_season", "N/A"),
            "description": d.get("description", ""),
            "source": "Web Search",
            "source_url": d.get("source_url", ""),
        }
        for d in destinations
    ]


def _extract_weather(state: TravelState) -> Dict | None:
    weather_results = state.get("weather_results", {})

    if not weather_results.get("success"):
        return None

    return weather_results.get("weather_info", {})


def _add_weather_to_recommendations(
    recommendations: List[Dict], weather_info: Dict
) -> List[Dict]:
    weather_destination = weather_info.get("destination", "").lower()

    for rec in recommendations:
        rec_dest = rec.get("destination", "").lower()
        rec_country = rec.get("country", "").lower()

        if (
            weather_destination in rec_dest
            or weather_destination in rec_country
            or rec_dest in weather_destination
        ):
            rec["weather"] = {
                "temperature": weather_info.get(
                    "temperature_range", "N/A"
                ),
                "conditions": weather_info.get("conditions", "N/A"),
                "rainfall": weather_info.get("rainfall", "N/A"),
                "summary": weather_info.get("summary", ""),
            }
            rec["best_time"] = weather_info.get(
                "best_time_to_visit", rec.get("best_season", "N/A")
            )

    return recommendations


def _deduplicate(destinations: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []

    for dest in destinations:
        key = dest.get("destination", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(dest)

    return unique


def _rank(destinations: List[Dict], user_prefs: Dict) -> List[Dict]:
    if not destinations:
        return []

    user_budget = user_prefs.get("budget_max")
    user_activities = set(user_prefs.get("activities", []))
    user_month = (user_prefs.get("travel_month") or "").lower()

    def score(dest: Dict) -> float:
        points = 0.0

        source = dest.get("source", "").lower()
        points += 100 if "pdf" in source else 80 if "database" in source else 25

        cost = dest.get("cost")
        if cost and cost != "N/A" and user_budget:
            try:
                cost_val = int(cost)
                if cost_val <= user_budget:
                    points += 20 + (cost_val / user_budget) * 10
                else:
                    points -= (
                        (cost_val - user_budget) / user_budget
                    ) * 20
            except Exception:
                pass

        if user_activities:
            activities = dest.get("activities", "").lower()
            points += sum(
                5 for act in user_activities if act.lower() in activities
            )

        if user_month and user_month in dest.get("best_season", "").lower():
            points += 15

        if dest.get("weather"):
            points += 10

        return points

    return sorted(destinations, key=score, reverse=True)

def display_results(response: dict):
    """Display formatted travel and weather results"""

    final_result = response.get("final_result")
    if not final_result:
        print("No results generated")
        return

    recommendations = final_result.get("recommendations", [])
    weather_info = final_result.get("weather_info")
    weather_only = final_result.get("weather_only", False)

    # Weather-only output
    if weather_only or (not recommendations and weather_info):
        print("\nWEATHER INFORMATION")
        print("-" * 50)

        if weather_info:
            print(f"Location     : {weather_info.get('destination', 'N/A')}")
            print(f"Temperature  : {weather_info.get('temperature_range', 'N/A')}")
            print(f"Conditions   : {weather_info.get('conditions', 'N/A')}")

            if weather_info.get("rainfall") not in (None, "N/A"):
                print(f"Rainfall     : {weather_info.get('rainfall')}")

            if weather_info.get("humidity") not in (None, "N/A"):
                print(f"Humidity     : {weather_info.get('humidity')}")

            if weather_info.get("wind_speed") not in (None, "N/A"):
                print(f"Wind Speed   : {weather_info.get('wind_speed')}")

            if weather_info.get("best_time_to_visit"):
                print(f"Best Time    : {weather_info.get('best_time_to_visit')}")

            if weather_info.get("summary"):
                print(f"\nSummary      : {weather_info.get('summary')}")

        print()
        return

    if not recommendations:
        print("No destinations found")
        return

    # Header
    print("\nTRAVEL RECOMMENDATIONS")
    print("-" * 50)
    print(f"Total Found : {final_result.get('total_found', 0)}")
    print(f"Source      : {final_result.get('data_source', 'unknown')}")
    print("-" * 50)

    # Top recommendations
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"\n{i}. {rec.get('destination', 'Unknown')}")
        print("-" * 50)

        if rec.get("country") not in (None, "N/A"):
            print(f"Country     : {rec['country']}")

        if rec.get("cost") not in (None, "N/A"):
            print(f"Cost        : ₹{rec['cost']}")

        if rec.get("rating") not in (None, "N/A"):
            print(f"Rating      : {rec['rating']}/5")

        if rec.get("weather"):
            w = rec["weather"]
            print(
                f"Weather     : {w.get('temperature', 'N/A')} | "
                f"{w.get('conditions', 'N/A')}"
            )
            if w.get("rainfall"):
                print(f"Rainfall    : {w.get('rainfall')}")

        if rec.get("description"):
            print(f"Description : {rec['description']}")

        if rec.get("activities"):
            print(f"Activities  : {rec['activities']}")

        if rec.get("best_season") not in (None, "N/A"):
            print(f"Best Season : {rec['best_season']}")
        elif rec.get("best_time") not in (None, "N/A"):
            print(f"Best Time   : {rec['best_time']}")

        if rec.get("duration"):
            print(f"Duration    : {rec['duration']}")

        if rec.get("source"):
            print(f"Source      : {rec['source']}")

        if rec.get("source_url"):
            print(f"URL         : {rec['source_url']}")

    print()

