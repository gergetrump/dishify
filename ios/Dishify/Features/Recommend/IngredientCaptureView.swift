import PhotosUI
import SwiftUI
import UIKit

struct IngredientCaptureView: View {
    let onConfirm: ([DetectedIngredient]) -> Void
    @Environment(\.dismiss) private var dismiss

    @State private var mode: CaptureMode = .choose
    @State private var image: UIImage?
    @State private var detected: [DetectedIngredient] = []
    @State private var selected = Set<Int>()
    @State private var isDetecting = false
    @State private var error: String?
    @State private var photoItem: PhotosPickerItem?

    private let api = APIClient()

    enum CaptureMode {
        case choose
        case review
    }

    var body: some View {
        NavigationStack {
            Group {
                switch mode {
                case .choose:
                    chooseView
                case .review:
                    reviewView
                }
            }
            .navigationTitle("Scan ingredients")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }

    private var chooseView: some View {
        VStack(spacing: Theme.Spacing.xl) {
            Text("Take a photo or upload an image of your ingredients.")
                .font(Theme.Fonts.body(16))
                .foregroundStyle(Theme.Colors.muted)
                .multilineTextAlignment(.center)

            if let error {
                AlertBanner(text: error)
            }

            PhotosPicker(selection: $photoItem, matching: .images) {
                Label("Upload photo", systemImage: "photo.on.rectangle")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(PrimaryButtonStyle())

            CameraCaptureButtonLabel { captured in
                Task { await runDetection(image: captured) }
            }
        }
        .padding(Theme.Spacing.screenPadding)
        .onChange(of: photoItem) { item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self),
                   let uiImage = UIImage(data: data) {
                    await runDetection(image: uiImage)
                }
            }
        }
    }

    private var reviewView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                if let image {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card))
                }

                if isDetecting {
                    LoadingState(message: "Detecting ingredients...")
                } else if let error {
                    AlertBanner(text: error)
                } else if detected.isEmpty {
                    EmptyState(text: "No ingredients recognized. Try a clearer photo.")
                } else {
                    Text("Select ingredients to add")
                        .font(Theme.Fonts.label(16, weight: .bold))
                    ForEach(Array(detected.enumerated()), id: \.offset) { index, item in
                        Button {
                            toggle(index)
                        } label: {
                            HStack {
                                Image(systemName: selected.contains(index) ? "checkmark.circle.fill" : "circle")
                                    .foregroundStyle(selected.contains(index) ? Theme.Colors.primary : Theme.Colors.muted)
                                VStack(alignment: .leading) {
                                    Text(item.name)
                                        .font(Theme.Fonts.label(16, weight: .semibold))
                                        .foregroundStyle(Theme.Colors.text)
                                    Text(item.rawText)
                                        .font(Theme.Fonts.body(14))
                                        .foregroundStyle(Theme.Colors.muted)
                                }
                                Spacer()
                            }
                            .padding(Theme.Spacing.md)
                            .background(Theme.Colors.cardBackground)
                            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card))
                        }
                    }

                    Button("Add selected") {
                        let chosen = detected.enumerated().compactMap { index, item in
                            selected.contains(index) ? item : nil
                        }
                        onConfirm(chosen)
                        dismiss()
                    }
                    .buttonStyle(PrimaryButtonStyle())
                    .disabled(selected.isEmpty)
                }
            }
            .padding(Theme.Spacing.screenPadding)
        }
    }

    private func toggle(_ index: Int) {
        if selected.contains(index) {
            selected.remove(index)
        } else {
            selected.insert(index)
        }
    }

    @MainActor
    private func runDetection(image: UIImage) async {
        mode = .review
        self.image = image
        detected = []
        selected = []
        error = nil
        isDetecting = true
        defer { isDetecting = false }

        guard let jpeg = image.jpegData(compressionQuality: 0.9) else {
            error = "Could not process the image."
            return
        }
        do {
            let response = try await api.detectIngredients(
                VisionIngredientsRequest(imageBase64: jpeg.base64EncodedString(), mimeType: "image/jpeg")
            )
            detected = response.ingredients
            selected = Set(detected.indices)
            if detected.isEmpty {
                error = "No ingredients recognized. Try a clearer photo."
            }
        } catch {
            self.error = error.localizedDescription
        }
    }
}

private struct CameraCaptureButton: UIViewControllerRepresentable {
    let onCapture: (UIImage) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onCapture: onCapture)
    }

    final class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onCapture: (UIImage) -> Void

        init(onCapture: @escaping (UIImage) -> Void) {
            self.onCapture = onCapture
        }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            picker.dismiss(animated: true)
            if let image = info[.originalImage] as? UIImage {
                onCapture(image)
            }
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true)
        }
    }
}

struct CameraCaptureButtonLabel: View {
    let onCapture: (UIImage) -> Void
    @State private var showCamera = false

    var body: some View {
        Button {
            showCamera = true
        } label: {
            Label("Take photo", systemImage: "camera")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(PrimaryButtonStyle(variant: .secondary))
        .fullScreenCover(isPresented: $showCamera) {
            CameraCaptureButton(onCapture: onCapture)
                .ignoresSafeArea()
        }
    }
}
