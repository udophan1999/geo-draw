import Foundation
@testable import MathMate

/// Answers every request of a URLSession with a canned response and records the requests.
final class StubProtocol: URLProtocol, @unchecked Sendable {
    struct Reply: Sendable {
        var status = 200
        var body = Data()
        var headers: [String: String] = ["Content-Type": "application/json"]
    }

    nonisolated(unsafe) static var replies: [String: Reply] = [:]
    /// Answers used once each, in order, before `replies` (e.g. a dropped stream, then a full one).
    nonisolated(unsafe) static var queued: [String: [Reply]] = [:]
    nonisolated(unsafe) static var requests: [URLRequest] = []
    nonisolated(unsafe) static var offline = false

    static func reset() {
        replies = [:]
        queued = [:]
        requests = []
        offline = false
    }

    static func reply(_ path: String, status: Int = 200, json: String, headers: [String: String] = [:]) {
        replies[path] = Reply(status: status, body: Data(json.utf8),
                              headers: ["Content-Type": "application/json"].merging(headers) { $1 })
    }

    static func queue(_ path: String, events: String) {
        queued[path, default: []].append(Reply(status: 200, body: Data(events.utf8),
                                               headers: ["Content-Type": "text/event-stream"]))
    }

    static func session() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubProtocol.self]
        return URLSession(configuration: configuration)
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        var recorded = request
        if recorded.httpBody == nil, let stream = request.httpBodyStream {
            stream.open()
            var data = Data()
            var buffer = [UInt8](repeating: 0, count: 4096)
            while stream.hasBytesAvailable {
                let count = stream.read(&buffer, maxLength: buffer.count)
                if count <= 0 { break }
                data.append(buffer, count: count)
            }
            stream.close()
            recorded.httpBody = data
        }
        Self.requests.append(recorded)
        if Self.offline {
            client?.urlProtocol(self, didFailWithError: URLError(.notConnectedToInternet))
            return
        }
        let path = request.url!.path
        let reply: Reply
        if var waiting = Self.queued[path], !waiting.isEmpty {
            reply = waiting.removeFirst()
            Self.queued[path] = waiting
        } else {
            reply = Self.replies[path] ?? Reply(status: 404, body: Data(#"{"detail":"Không tìm thấy."}"#.utf8))
        }
        let response = HTTPURLResponse(url: request.url!, statusCode: reply.status, httpVersion: "HTTP/1.1",
                                       headerFields: reply.headers)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: reply.body)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}
