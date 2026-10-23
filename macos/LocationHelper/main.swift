import CoreLocation
import Foundation

final class Delegate: NSObject, CLLocationManagerDelegate {
    private let manager: CLLocationManager

    init(_ manager: CLLocationManager) {
        self.manager = manager
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status: CLAuthorizationStatus
        if #available(macOS 11.0, *) {
            status = manager.authorizationStatus
        } else {
            status = CLLocationManager.authorizationStatus()
        }
        switch status {
        case .authorized, .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .denied, .restricted:
            exit(1)
        case .notDetermined:
            break
        @unknown default:
            exit(1)
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        let output: [String: Any] = [
            "latitude": location.coordinate.latitude,
            "longitude": location.coordinate.longitude,
            "accuracy": location.horizontalAccuracy,
        ]
        if let data = try? JSONSerialization.data(withJSONObject: output),
           let text = String(data: data, encoding: .utf8) {
            print(text)
        }
        exit(0)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        fputs("location unavailable: \(error)\n", stderr)
        exit(1)
    }
}

let manager = CLLocationManager()
let delegate = Delegate(manager)
manager.delegate = delegate
manager.requestWhenInUseAuthorization()
RunLoop.main.run(until: Date(timeIntervalSinceNow: 10))
exit(1)
