import React from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { EnvironmentOutlined, ClockCircleOutlined, CarOutlined, AimOutlined } from '@ant-design/icons'

// Fix default marker icon for Leaflet in bundler environment
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

export interface TravelInfo {
  mode: string
  icon: string
  distance_km: number
  duration_hours: number
  duration_text: string
}

export interface MapData {
  place: string
  lat: number
  lon: number
  display_name: string
  timezone: string
  local_time: string
  weekday: string
  travel_info: TravelInfo[]
}

interface MapViewProps {
  data: MapData
}

const MapView: React.FC<MapViewProps> = ({ data }) => {
  const { lat, lon, display_name, timezone, local_time, weekday, travel_info } = data

  return (
    <div className="map-container">
      <div className="map-header">
        <div className="map-title">
          <EnvironmentOutlined style={{ marginRight: 6, color: '#1677ff' }} />
          {display_name}
        </div>
      </div>

      <div className="map-body">
        <MapContainer
          center={[lat, lon]}
          zoom={11}
          scrollWheelZoom={false}
          style={{ height: '280px', width: '100%' }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap'
          />
          <Marker position={[lat, lon]}>
            <Popup>{display_name}</Popup>
          </Marker>
        </MapContainer>
      </div>

      <div className="map-info-panel">
        <div className="map-info-row">
          <ClockCircleOutlined style={{ marginRight: 6, color: '#1677ff' }} />
          <span className="map-info-label">当地时间</span>
          <span className="map-info-value">{local_time} ({weekday})</span>
        </div>
        <div className="map-info-row">
          <EnvironmentOutlined style={{ marginRight: 6, color: '#52c41a' }} />
          <span className="map-info-label">时区</span>
          <span className="map-info-value">{timezone}</span>
        </div>
        <span className="map-info-coords">坐标: {lat.toFixed(4)}, {lon.toFixed(4)}</span>
      </div>

      {travel_info && travel_info.length > 0 && (
        <div className="map-travel-panel">
          <div className="map-travel-title">
            <CarOutlined style={{ marginRight: 6 }} />
            出行方式参考
          </div>
          <div className="map-travel-list">
            {travel_info.map((t, i) => (
              <div key={i} className="map-travel-item">
                <span className="map-travel-mode">{t.mode}</span>
                <span className="map-travel-distance">{t.distance_km} km</span>
                <span className="map-travel-duration">约 {t.duration_text}</span>
              </div>
            ))}
          </div>
          <div className="map-travel-hint">
            <AimOutlined style={{ marginRight: 4, fontSize: 11 }} />
            出行时间基于您的当前位置估算
          </div>
        </div>
      )}
    </div>
  )
}

export default MapView
