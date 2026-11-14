import { Card } from '../components/ui'

export function AboutPage() {
  return (
    <div className="page prose">
      <div className="page-head">
        <h1>About HeatShield</h1>
        <p className="lede">Heat-stress warnings for people who work outdoors, starting in Mumbai and working for any location.</p>
      </div>
      <Card title="Why not just the temperature?">
        <p>
          Mumbai's heat is dangerous because of humidity as much as temperature. When the air is humid, sweat cannot cool the body. HeatShield uses
          <strong> Wet Bulb Globe Temperature (WBGT)</strong>, the measure used to set safe work limits around the world. It combines temperature, humidity, sun and wind.
        </p>
      </Card>
      <Card title="How the numbers are made">
        <ol>
          <li>Hourly weather forecast from Open-Meteo (temperature, humidity, wind, sunshine, pressure).</li>
          <li>WBGT for each hour with the Liljegren (2008) physics model, checked against ECMWF's thermofeel to within 0.01 °C.</li>
          <li>The safe limit for your type of work from NIOSH (2016) and ISO 7243, with stricter limits for people new to the heat.</li>
          <li>Minutes of work and rest per hour so your average effort stays under the limit, rounded down to be safe.</li>
        </ol>
        <p>
          Risk levels: <strong>Safe</strong> is more than 2° under the limit, <strong>Caution</strong> is within 2°, <strong>High</strong> is over the limit but some work is allowed each hour, and <strong>Extreme</strong> means stop that work.
        </p>
      </Card>
      <Card title="Mumbai coverage">
        <p>
          Alerts and the map cover all 24 BMC wards. Six focus wards with contrasting conditions are used for checking accuracy: M/E (Govandi, Mankhurd), L (Kurla), G/N (Dharavi, Dadar), K/E (Andheri East), A (Colaba) and P/S (Goregaon, Aarey).
        </p>
        <p>The weather model has a grid of about 10 km, so neighbouring wards can show the same values today. A street-level model trained on satellite data is coming next.</p>
      </Card>
      <Card title="Privacy">
        <p>
          Your location is rounded to about 1 km before it is stored. Your account lives on your device with no password or phone number required. You can pause or delete everything at any time from My alerts.
        </p>
      </Card>
      <Card title="For developers">
        <p>
          The open API is documented at <a href="/api/docs">/api/docs</a>.
        </p>
      </Card>
    </div>
  )
}
