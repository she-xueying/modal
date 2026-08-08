import React from 'react'
import { EnvironmentOutlined } from '@ant-design/icons'

export interface CurrentWeather {
  temperature: number | null
  apparent_temperature: number | null
  humidity: number | null
  precipitation: number | null
  wind_speed: number | null
  wind_direction: number | null
  wind_dir_text: string
  weather_code: number | null
  condition: string
  is_day: boolean
}

export interface DailyWeather {
  weather_code: number | null
  condition: string
  temp_max: number | null
  temp_min: number | null
}

export interface WeatherData {
  place: string
  display_name: string
  lat: number
  lon: number
  current: CurrentWeather
  today: DailyWeather
}

interface WeatherCardProps {
  data: WeatherData
}

/** Map WMO weather code to an emoji. */
function weatherEmoji(code: number | null, isDay: boolean): string {
  if (code == null) return '🌡️'
  if (code === 0) return isDay ? '☀️' : '🌙'
  if (code === 1 || code === 2) return '🌤️'
  if (code === 3) return '☁️'
  if (code >= 45 && code <= 48) return '🌫️'
  if (code >= 51 && code <= 57) return '🌦️'
  if (code >= 61 && code <= 67) return '🌧️'
  if (code >= 71 && code <= 77) return '❄️'
  if (code >= 80 && code <= 82) return '🌧️'
  if (code >= 85 && code <= 86) return '🌨️'
  if (code >= 95) return '⛈️'
  return '🌡️'
}

const WeatherCard: React.FC<WeatherCardProps> = ({ data }) => {
  const { display_name, current, today } = data
  const emoji = weatherEmoji(current.weather_code, current.is_day)

  return (
    <div className="weather-container">
      <div className="weather-header">
        <div className="weather-title">
          <EnvironmentOutlined style={{ marginRight: 6, color: '#1677ff' }} />
          {display_name}
        </div>
        <span className="weather-cond-text">{current.condition}</span>
      </div>

      <div className="weather-main">
        <span className="weather-emoji">{emoji}</span>
        <div className="weather-temp-block">
          <span className="weather-temp">
            {current.temperature != null ? `${Math.round(current.temperature)}°C` : '--'}
          </span>
          <span className="weather-feels">
            体感 {current.apparent_temperature != null ? `${Math.round(current.apparent_temperature)}°C` : '--'}
          </span>
        </div>
        <div className="weather-today">
          <div className="weather-today-cond">{today.condition}</div>
          <div className="weather-today-temp">
            {today.temp_min != null ? `${Math.round(today.temp_min)}°` : '--'}
            {' ~ '}
            {today.temp_max != null ? `${Math.round(today.temp_max)}°` : '--'}
          </div>
        </div>
      </div>

      <div className="weather-details">
        <div className="weather-detail-item">
          <span className="weather-detail-icon">💧</span>
          <span className="weather-detail-label">湿度</span>
          <span className="weather-detail-value">
            {current.humidity != null ? `${current.humidity}%` : '--'}
          </span>
        </div>
        <div className="weather-detail-item">
          <span className="weather-detail-icon">🌬️</span>
          <span className="weather-detail-label">风力</span>
          <span className="weather-detail-value">
            {current.wind_speed != null
              ? `${current.wind_dir_text} ${Math.round(current.wind_speed)}km/h`
              : '--'}
          </span>
        </div>
        <div className="weather-detail-item">
          <span className="weather-detail-icon">☔</span>
          <span className="weather-detail-label">降水</span>
          <span className="weather-detail-value">
            {current.precipitation != null ? `${current.precipitation}mm` : '--'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default WeatherCard