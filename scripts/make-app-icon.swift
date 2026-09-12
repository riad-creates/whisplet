import AppKit

let destination = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let variants = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]

func render(size: Int, to url: URL) throws {
    let dimension = CGFloat(size)
    let image = NSImage(size: NSSize(width: dimension, height: dimension))
    image.lockFocus()

    let bounds = NSRect(x: 0, y: 0, width: dimension, height: dimension)
    let inset = dimension * 0.07
    let tile = NSBezierPath(
        roundedRect: bounds.insetBy(dx: inset, dy: inset),
        xRadius: dimension * 0.23,
        yRadius: dimension * 0.23
    )
    NSColor(calibratedRed: 0.965, green: 0.965, blue: 0.99, alpha: 1).setFill()
    tile.fill()
    let mark = NSBezierPath()
    mark.lineWidth = max(1.0, dimension * 0.052)
    mark.lineCapStyle = .round
    mark.move(to: NSPoint(x: dimension * 0.22, y: dimension * 0.5))
    mark.curve(to: NSPoint(x: dimension * 0.43, y: dimension * 0.5),
        controlPoint1: NSPoint(x: dimension * 0.29, y: dimension * 0.815),
        controlPoint2: NSPoint(x: dimension * 0.36, y: dimension * 0.185))
    mark.curve(to: NSPoint(x: dimension * 0.64, y: dimension * 0.5),
        controlPoint1: NSPoint(x: dimension * 0.50, y: dimension * 0.815),
        controlPoint2: NSPoint(x: dimension * 0.57, y: dimension * 0.185))
    NSColor(calibratedRed: 0.31, green: 0.29, blue: 0.78, alpha: 1).setStroke()
    mark.stroke()
    let cursor = NSBezierPath(roundedRect: NSRect(x: dimension * 0.742,
        y: dimension * 0.318, width: dimension * 0.049, height: dimension * 0.364),
        xRadius: dimension * 0.0245, yRadius: dimension * 0.0245)
    NSColor(calibratedRed: 0.12, green: 0.13, blue: 0.18, alpha: 1).setFill()
    cursor.fill()

    image.unlockFocus()
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:])
    else { throw CocoaError(.fileWriteUnknown) }
    try png.write(to: url)
}

for (name, size) in variants {
    try render(size: size, to: destination.appendingPathComponent(name))
}
