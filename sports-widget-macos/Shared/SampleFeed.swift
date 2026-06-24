import Foundation

// Static sample used for SwiftUI previews, the widget gallery snapshot, and as
// an offline fallback. Trimmed copy of the real feed schema (snake_case keys).
enum SampleFeed {
    static let json = """
    {
      "f1": {
        "next": {
          "name": "FORMULA 1 AUSTRIAN GRAND PRIX",
          "short_name": "Austrian Grand Prix",
          "round": 1288,
          "circuit": "Spielberg",
          "location": "Spielberg",
          "country": "Austria",
          "flag_emoji": "🇦🇹",
          "external_url": "https://www.formula1.com/en/racing/2026.html",
          "sessions": [
            {"type": "FP1", "start_utc": "2026-06-26T11:30:00+00:00", "start_ist": "2026-06-26T17:00:00+05:30"},
            {"type": "FP2", "start_utc": "2026-06-26T15:00:00+00:00", "start_ist": "2026-06-26T20:30:00+05:30"},
            {"type": "FP3", "start_utc": "2026-06-27T10:30:00+00:00", "start_ist": "2026-06-27T16:00:00+05:30"},
            {"type": "Qualifying", "start_utc": "2026-06-27T14:00:00+00:00", "start_ist": "2026-06-27T19:30:00+05:30"},
            {"type": "Race", "start_utc": "2026-06-28T13:00:00+00:00", "start_ist": "2026-06-28T18:30:00+05:30"}
          ]
        },
        "upcoming": [],
        "standings": {
          "drivers": [
            {"position": 1, "code": "ANT", "name": "Antonelli", "points": 156, "team": "Mercedes", "color": "#27F4D2"},
            {"position": 2, "code": "HAM", "name": "Hamilton", "points": 115, "team": "Ferrari", "color": "#E8002D"},
            {"position": 3, "code": "RUS", "name": "Russell", "points": 106, "team": "Mercedes", "color": "#27F4D2"},
            {"position": 4, "code": "LEC", "name": "Leclerc", "points": 75, "team": "Ferrari", "color": "#E8002D"},
            {"position": 5, "code": "NOR", "name": "Norris", "points": 73, "team": "McLaren", "color": "#FF8000"}
          ],
          "constructors": [
            {"position": 1, "name": "Mercedes", "points": 262, "color": "#27F4D2"},
            {"position": 2, "name": "Ferrari", "points": 190, "color": "#E8002D"},
            {"position": 3, "name": "McLaren", "points": 141, "color": "#FF8000"},
            {"position": 4, "name": "Red Bull", "points": 89, "color": "#3671C6"},
            {"position": 5, "name": "Alpine F1 Team", "points": 57, "color": "#0093CC"}
          ]
        }
      },
      "ufc": {
        "next": {
          "name": "UFC Fight Night: Fiziev vs Torres",
          "kind": "Fight Night",
          "venue": "National Gymnastics Arena",
          "city": "Baku Azerbaijan",
          "country": "",
          "main_card_start_utc": "2026-06-27T16:00:00Z",
          "main_card_start_ist": "2026-06-27T21:30:00+05:30",
          "url": "https://www.ufc.com/event/ufc-fight-night-june-27-2026",
          "main_card": [
            {"red": "Rafael Fiziev", "blue": "Manuel Torres", "red_rank": "#11", "blue_rank": "#15", "red_odds": "-115", "blue_odds": "-105", "red_country": "Azerbaijan", "blue_country": "Mexico", "red_img": "", "blue_img": "", "weight_class": "Lightweight Bout", "title_fight": false},
            {"red": "Shara Magomedov", "blue": "Michel Pereira", "red_rank": "", "blue_rank": "", "red_odds": "-340", "blue_odds": "+265", "red_country": "Russia", "blue_country": "Brazil", "red_img": "", "blue_img": "", "weight_class": "Middleweight Bout", "title_fight": false},
            {"red": "Arman Tsarukyan", "blue": "Dan Hooker", "red_rank": "#1", "blue_rank": "#7", "red_odds": "-450", "blue_odds": "+330", "red_country": "Armenia", "blue_country": "New Zealand", "red_img": "", "blue_img": "", "weight_class": "Lightweight Bout", "title_fight": false},
            {"red": "Tom Aspinall", "blue": "Ciryl Gane", "red_rank": "C", "blue_rank": "#1", "red_odds": "-200", "blue_odds": "+170", "red_country": "United Kingdom", "blue_country": "France", "red_img": "", "blue_img": "", "weight_class": "Heavyweight Title Bout", "title_fight": true}
          ]
        },
        "upcoming": [
          {"name": "UFC 320: Pereira vs Ankalaev", "kind": "PPV", "city": "Las Vegas", "main_card_start_utc": "2026-07-12T02:00:00Z", "url": "https://www.ufc.com/event/ufc-320"},
          {"name": "UFC Fight Night: Hill vs Rountree", "kind": "Fight Night", "city": "Las Vegas", "main_card_start_utc": "2026-07-19T22:00:00Z", "url": "https://www.ufc.com/event/ufc-fight-night-july-19"},
          {"name": "UFC Fight Night: Dvalishvili vs Yan", "kind": "Fight Night", "city": "Abu Dhabi", "main_card_start_utc": "2026-07-26T18:00:00Z", "url": "https://www.ufc.com/event/ufc-fight-night-july-26"}
        ]
      }
    }
    """
}
