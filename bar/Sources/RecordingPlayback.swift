import AVFoundation
import Foundation

@MainActor
final class RecordingPlayback: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var playingID: String?
    private var player: AVAudioPlayer?

    func toggle(_ item: NativeHistoryItem) throws {
        let wasPlaying = playingID == item.id
        stop()
        guard !wasPlaying else { return }
        let next = try AVAudioPlayer(contentsOf: item.directoryURL.appendingPathComponent(item.metadata.audioFile))
        next.delegate = self
        player = next
        guard next.play() else { throw CocoaError(.fileReadUnknown) }
        playingID = item.id
    }

    func stop() {
        player?.stop()
        player = nil
        playingID = nil
    }

    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor in
            if self.player === player { self.stop() }
        }
    }
}
