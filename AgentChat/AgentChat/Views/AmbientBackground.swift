import SwiftUI

/// Мягкий анимированный фон: плавно дрейфующие размытые пятна. Минималистично,
/// адаптируется под светлую/тёмную тему.
struct AmbientBackground: View {
    @Environment(\.colorScheme) private var scheme

    private struct Blob {
        let color: Color
        let size: CGFloat
        let ampX: CGFloat
        let ampY: CGFloat
        let speed: Double
        let phase: Double
    }

    var body: some View {
        GeometryReader { geo in
            TimelineView(.animation) { timeline in
                let t = timeline.date.timeIntervalSinceReferenceDate
                let w = geo.size.width
                let h = geo.size.height

                ZStack {
                    base
                    ForEach(blobs.indices, id: \.self) { i in
                        let blob = blobs[i]
                        Circle()
                            .fill(blob.color)
                            .frame(width: blob.size, height: blob.size)
                            .position(
                                x: w * (0.5 + blob.ampX * CGFloat(sin(t * blob.speed + blob.phase))),
                                y: h * (0.5 + blob.ampY * CGFloat(cos(t * blob.speed * 0.8 + blob.phase)))
                            )
                    }
                }
                .blur(radius: 80)
            }
        }
        .ignoresSafeArea()
    }

    private var base: Color {
        scheme == .dark ? Color(white: 0.05) : Color(white: 0.97)
    }

    private var blobs: [Blob] {
        if scheme == .dark {
            return [
                Blob(color: Color(red: 0.20, green: 0.18, blue: 0.45).opacity(0.85), size: 460, ampX: 0.30, ampY: 0.28, speed: 0.06, phase: 0.0),
                Blob(color: Color(red: 0.10, green: 0.30, blue: 0.42).opacity(0.80), size: 420, ampX: 0.32, ampY: 0.30, speed: 0.05, phase: 2.1),
                Blob(color: Color(red: 0.32, green: 0.15, blue: 0.40).opacity(0.75), size: 400, ampX: 0.28, ampY: 0.26, speed: 0.07, phase: 4.0)
            ]
        } else {
            return [
                Blob(color: Color(red: 0.62, green: 0.78, blue: 1.00).opacity(0.70), size: 440, ampX: 0.30, ampY: 0.28, speed: 0.06, phase: 0.0),
                Blob(color: Color(red: 1.00, green: 0.80, blue: 0.86).opacity(0.65), size: 420, ampX: 0.32, ampY: 0.30, speed: 0.05, phase: 2.1),
                Blob(color: Color(red: 0.80, green: 0.95, blue: 0.88).opacity(0.65), size: 400, ampX: 0.28, ampY: 0.26, speed: 0.07, phase: 4.0)
            ]
        }
    }
}
