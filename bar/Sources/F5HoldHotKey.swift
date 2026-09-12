import Carbon
import Foundation

struct HoldKeyEdges {
    private(set) var isDown = false

    mutating func receive(pressed: Bool) -> Bool? {
        guard pressed != isDown else { return nil }
        isDown = pressed
        return pressed
    }
}

/// Registers only while selected, so other apps retain F5 in other modes.
@MainActor
final class F5HoldHotKey {
    private var hotKey: EventHotKeyRef?
    private var handler: EventHandlerRef?
    private var edges = HoldKeyEdges()
    var onChange: ((Bool, UInt64) -> Void)?

    @discardableResult
    func setEnabled(_ enabled: Bool) -> Bool {
        if !enabled {
            if let hotKey { UnregisterEventHotKey(hotKey) }
            if let handler { RemoveEventHandler(handler) }
            hotKey = nil
            handler = nil
            if edges.receive(pressed: false) != nil {
                onChange?(false, DispatchTime.now().uptimeNanoseconds)
            }
            return true
        }
        if hotKey != nil { return true }
        var specs = [
            EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed)),
            EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyReleased)),
        ]
        let callback: EventHandlerUPP = { _, event, context in
            guard let event, let context else { return OSStatus(eventNotHandledErr) }
            var identity = EventHotKeyID()
            let status = GetEventParameter(event, EventParamName(kEventParamDirectObject),
                EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size,
                nil, &identity)
            guard status == noErr, identity.signature == 0x57485350, identity.id == 5 else {
                return OSStatus(eventNotHandledErr)
            }
            let owner = Unmanaged<F5HoldHotKey>.fromOpaque(context).takeUnretainedValue()
            let pressed = GetEventKind(event) == UInt32(kEventHotKeyPressed)
            let timestamp = DispatchTime.now().uptimeNanoseconds
            Task { @MainActor in
                guard owner.hotKey != nil, let edge = owner.edges.receive(pressed: pressed) else { return }
                owner.onChange?(edge, timestamp)
            }
            return noErr
        }
        let handlerStatus = InstallEventHandler(GetApplicationEventTarget(), callback,
            specs.count, &specs, Unmanaged.passUnretained(self).toOpaque(), &handler)
        guard handlerStatus == noErr else {
            setEnabled(false)
            return false
        }
        let status = RegisterEventHotKey(UInt32(kVK_F5), 0,
            EventHotKeyID(signature: 0x57485350, id: 5), GetApplicationEventTarget(), 0, &hotKey)
        if status != noErr {
            setEnabled(false)
            return false
        }
        return true
    }
}
