import AVFoundation
import Foundation

enum VoiceInputError: LocalizedError {
    case permissionDenied
    case recorderUnavailable
    case emptyRecording

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Microphone access is required for voice input."
        case .recorderUnavailable:
            return "Voice recording is not available on this device."
        case .emptyRecording:
            return "No audio was captured. Try again."
        }
    }
}

@MainActor
final class VoiceInputService: NSObject, AVAudioRecorderDelegate {
    private var recorder: AVAudioRecorder?
    private var fileURL: URL?

    func startRecording() async throws {
        let granted = await requestPermission()
        guard granted else { throw VoiceInputError.permissionDenied }

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker])
        try session.setActive(true)

        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("dishify-voice-\(UUID().uuidString).m4a")
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44_100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
        ]
        recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder?.delegate = self
        guard recorder?.prepareToRecord() == true, recorder?.record() == true else {
            throw VoiceInputError.recorderUnavailable
        }
        fileURL = url
    }

    func stopAndTranscribe(api: APIClient) async throws -> VoiceResponse {
        recorder?.stop()
        recorder = nil
        defer {
            try? AVAudioSession.sharedInstance().setActive(false)
        }
        guard let fileURL else { throw VoiceInputError.emptyRecording }
        let data = try Data(contentsOf: fileURL)
        guard !data.isEmpty else { throw VoiceInputError.emptyRecording }
        let base64 = data.base64EncodedString()
        try? FileManager.default.removeItem(at: fileURL)
        self.fileURL = nil
        return try await api.voice(VoiceRequest(audioBase64: base64, mimeType: "audio/mp4", language: nil))
    }

    private func requestPermission() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }
}
