import React from 'react'
import { EnvironmentOutlined, StarOutlined } from '@ant-design/icons'
import { message as antdMessage, Popconfirm } from 'antd'
import { WeatherData } from '../services/api'
import { useStore } from '../stores/useStore'

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

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function dateWeekday(dateStr?: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return WEEKDAYS[d.getDay()] || ''
}

function fmtTemp(v: number | null | undefined): string {
  return v != null ? `${Math.round(v)}°` : '--'
}

function fmtVisibility(m: number | null | undefined): string {
  if (m == null) return '--'
  return m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${Math.round(m)}m`
}

interface WeatherCardProps {
  data: WeatherData
}

const WeatherCard: React.FC<WeatherCardProps> = ({ data }) => {
  const { display_name, current, daily, hourly } = data
  const today = daily && daily.length > 0 ? daily[0] : data.today

  const defaultLocation = useStore((s) => s.defaultLocation)
  const setDefaultWeatherLocation = useStore((s) => s.setDefaultWeatherLocation)
  const clearDefaultWeatherLocation = useStore((s) => s.clearDefaultWeatherLocation)

  // Whether this card's place is the currently saved default
  const isCurrentDefault =
    !!defaultLocation &&
    Math.abs(defaultLocation.lat - data.lat) < 0.01 &&
    Math.abs(defaultLocation.lon - data.lon) < 0.01

  // Only explicit places can be set as default ("我的位置" cannot be geocoded later)
  const canSetDefault = !!data.place && data.place !== '我的位置'

  const emoji = weatherEmoji(current.weather_code, current.is_day)

  const handleSetDefault = async () => {
    try {
      await setDefaultWeatherLocation({
        place: data.place,
        display_name: data.display_name,
        lat: data.lat,
        lon: data.lon,
      })
      antdMessage.success(`已将 ${data.display_name} 设为默认地点`)
    } catch {
      antdMessage.error('设置默认地点失败')
    }
  }

  const handleClearDefault = async () => {
    try {
      await clearDefaultWeatherLocation()
      antdMessage.success('已清除默认地点')
    } catch {
      antdMessage.error('清除默认地点失败')
    }
  }

  return (
    <div className="weather-container">
      <div className="weather-header">
        <div className="weather-title">
          <EnvironmentOutlined style={{ marginRight: 6, color: '#1677ff' }} />
          {display_name}
          {isCurrentDefault && (
            <span className="weather-default-badge">
              <StarOutlined style={{ marginRight: 3 }} />
              默认
            </span>
          )}
        </div>
        <span className="weather-cond-text">{current.condition}</span>
      </div>

      <div className="weather-main">
        <span className="weather-emoji">{emoji}</span>
        <div className="weather-temp-block">
          <span className="weather-temp">{fmtTemp(current.temperature)}C</span>
          <span className="weather-feels">
            体感 {current.apparent_temperature != null ? `${Math.round(current.apparent_temperature)}°C` : '--'}
          </span>
        </div>
        <div className="weather-today">
          <div className="weather-today-cond">{today?.condition}</div>
          <div className="weather-today-temp">
            {fmtTemp(today?.temp_min)} ~ {fmtTemp(today?.temp_max)}
          </div>
          {today?.sunrise && (
            <div className="weather-suntimes">
              日出 {today.sunrise} · 日落 {today.sunset}
            </div>
          )}
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
              ? `${current.wind_dir_text} ${Math.round(current.wind_speed)}`
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
        <div className="weather-detail-item">
          <span className="weather-detail-icon">☀️</span>
          <span className="weather-detail-label">紫外线</span>
          <span className="weather-detail-value">
            {current.uv_index != null ? current.uv_index : '--'}
          </span>
        </div>
        <div className="weather-detail-item">
          <span className="weather-detail-icon">☁️</span>
          <span className="weather-detail-label">云量</span>
          <span className="weather-detail-value">
            {current.cloud_cover != null ? `${current.cloud_cover}%` : '--'}
          </span>
        </div>
        <div className="weather-detail-item">
          <span className="weather-detail-icon">🕵️</span>
          <span className="weather-detail-label">气压</span>
          <span className="weather-detail-value">
            {current.pressure != null ? `${Math.round(current.pressure)}hPa` : '--'}
          </span>
        </div>
        <div className="weather-detail-item">
          <span className="weather-detail-icon">👁️</span>
          <span className="weather-detail-label">能见度</span>
          <span className="weather-detail-value">{fmtVisibility(current.visibility)}</span>
        </div>
        <div className="weather-detail-item">
          <span className="weather-detail-icon">🌧️</span>
          <span className="weather-detail-label">降雨概率</span>
          <span className="weather-detail-value">
            {current.precipitation_probability != null
              ? `${current.precipitation_probability}%`
              : '--'}
          </span>
        </div>
      </div>

      {hourly && hourly.length > 0 && (
        <div className="weather-hourly">
          <div className="weather-section-title">未来 24 小时（每 3 小时）</div>
          <div className="weather-hourly-scroll">
            {hourly.map((h, i) => (
              <div key={i} className="weather-hourly-item">
                <span className="weather-hourly-time">{h.time}</span>
                <span className="weather-hourly-emoji">
                  {weatherEmoji(h.weather_code, true)}
                </span>
                <span className="weather-hourly-temp">{fmtTemp(h.temperature)}</span>
                {h.precip_prob != null && h.precip_prob > 0 && (
                  <span className="weather-hourly-rain">{h.precip_prob}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {daily && daily.length > 0 && (
        <div className="weather-week">
          <div className="weather-section-title">未来 7 天预报</div>
          {daily.map((d, i) => (
            <div key={i} className={`weather-day${i === 0 ? ' today' : ''}`}>
              <span className="weather-day-name">{i === 0 ? '今天' : dateWeekday(d.date)}</span>
              <span className="weather-day-emoji">{weatherEmoji(d.weather_code, true)}</span>
              <span className="weather-day-cond">{d.condition}</span>
              <span className="weather-day-rain">
                {d.precip_prob != null ? `💧${d.precip_prob}%` : ''}
              </span>
              <span className="weather-day-temp">
                {fmtTemp(d.temp_min)} ~ {fmtTemp(d.temp_max)}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="weather-footer">
        {canSetDefault &&
          (isCurrentDefault ? (
            <span
              className="weather-default-action is-default"
              onClick={handleClearDefault}
              title="点击清除默认地点"
            >
              <StarOutlined style={{ marginRight: 4 }} />
              已设为默认地点（点击清除）
            </span>
          ) : (
            <Popconfirm
              title="设为默认地点？"
              description={`设置后，未指定地点的天气查询将优先使用 ${display_name}`}
              okText="设为默认"
              cancelText="取消"
              onConfirm={handleSetDefault}
            >
              <span className="weather-default-action">
                <StarOutlined style={{ marginRight: 4 }} />
                设为默认地点
              </span>
            </Popconfirm>
          ))}
        {defaultLocation && !isCurrentDefault && (
          <span className="weather-default-current">
            当前默认：{defaultLocation.display_name}
          </span>
        )}
      </div>
    </div>
  )
}

export default WeatherCard