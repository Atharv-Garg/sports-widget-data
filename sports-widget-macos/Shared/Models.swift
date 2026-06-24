import Foundation

// Codable models mapping 1:1 to docs/feed.json.
// Decoded with JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase, so
// JSON keys like "short_name" / "main_card_start_utc" become camelCase here.
// All fields are optional so a partial/degraded feed never crashes the widget.

struct Feed: Decodable {
    let f1: F1Data?
    let ufc: UFCData?
}

// MARK: - F1

struct F1Data: Decodable {
    let next: F1Event?
    let upcoming: [F1Event]?
    let standings: Standings?
}

struct F1Event: Decodable {
    let name: String?
    let shortName: String?
    let round: Int?
    let circuit: String?
    let location: String?
    let country: String?
    let flagEmoji: String?
    let externalUrl: String?
    let sessions: [Session]?
}

struct Session: Decodable {
    let type: String?
    let startUtc: String?
    let endUtc: String?
    let startIst: String?
    let endIst: String?
}

struct Standings: Decodable {
    let drivers: [DriverStanding]?
    let constructors: [ConstructorStanding]?
}

struct DriverStanding: Decodable, Identifiable {
    let position: Int?
    let code: String?
    let name: String?
    let points: Double?
    let team: String?
    let color: String?
    var id: Int { position ?? 0 }
}

struct ConstructorStanding: Decodable, Identifiable {
    let position: Int?
    let name: String?
    let points: Double?
    let color: String?
    var id: Int { position ?? 0 }
}

// MARK: - UFC

struct UFCData: Decodable {
    let next: UFCEvent?
    let upcoming: [UFCEvent]?
}

struct UFCEvent: Decodable {
    let name: String?
    let kind: String?
    let venue: String?
    let city: String?
    let country: String?
    let mainCardStartUtc: String?
    let mainCardStartIst: String?
    let url: String?
    let mainCard: [Fight]?
}

struct Fight: Decodable, Identifiable {
    let red: String?
    let blue: String?
    let redRank: String?
    let blueRank: String?
    let redOdds: String?
    let blueOdds: String?
    let redCountry: String?
    let blueCountry: String?
    let redImg: String?
    let blueImg: String?
    let weightClass: String?
    let titleFight: Bool?
    var id: String { (red ?? "") + (blue ?? "") }
}
