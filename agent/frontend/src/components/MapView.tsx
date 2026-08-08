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

// ------------------------------------------------------------------ //
//  Coordinate conversion: WGS-84 -> GCJ-02
//  国内地图瓦片使用 GCJ-02 坐标系，需将 Nominatim 返回的 WGS-84 转换
// ------------------------------------------------------------------ //

const GCJ_A = 6378245.0
const GCJ_EE = 0.00669342162296594323

function _transformLat(x: number, y: number): number {
  let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  ret += ((20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin((y / 3.0) * Math.PI)) * 2.0) / 3.0
  ret += ((160.0 * Math.sin((y / 12.0) * Math.PI) + 320.0 * Math.sin((y * Math.PI) / 30.0)) * 2.0) / 3.0
  return ret
}

function _transformLon(x: number, y: number): number {
  let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  ret += ((20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin((x / 3.0) * Math.PI)) * 2.0) / 3.0
  ret += ((150.0 * Math.sin((x / 12.0) * Math.PI) + 300.0 * Math.sin((x / 30.0) * Math.PI)) * 2.0) / 3.0
  return ret
}

function _outOfChina(lat: number, lon: number): boolean {
  return lon < 72.004 || lon > 137.8347 || lat < 0.8293 || lat > 55.8271
}

/** Convert WGS-84 to GCJ-02, returns [lat, lon]. */
export function wgs84ToGcj02(lat: number, lon: number): [number, number] {
  if (_outOfChina(lat, lon)) return [lat, lon]
  let dLat = _transformLat(lon - 105.0, lat - 35.0)
  let dLon = _transformLon(lon - 105.0, lat - 35.0)
  const radLat = (lat / 180.0) * Math.PI
  let magic = Math.sin(radLat)
  magic = 1 - GCJ_EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / ((GCJ_A * (1 - GCJ_EE)) / (magic * sqrtMagic) * Math.PI)
  dLon = (dLon * 180.0) / ((GCJ_A / sqrtMagic) * Math.cos(radLat) * Math.PI)
  return [lat + dLat, lon + dLon]
}

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
  const [mapLat, mapLon] = wgs84ToGcj02(lat, lon)

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
          center={[mapLat, mapLon]}
          zoom={11}
          scrollWheelZoom={false}
          style={{ height: '280px', width: '100%' }}
        >
          <TileLayer
            url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
            subdomains="1234"
            maxZoom={18}
            attribution='&copy; AutoNavi'
          />
          <Marker position={[mapLat, mapLon]}>
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