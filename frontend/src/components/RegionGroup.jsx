import CityCard from './CityCard';

export default function RegionGroup({ region, cities, onSelectCity }) {
  return (
    <section className="mb-8">
      {/* Region header */}
      <div className="flex items-center gap-3 mb-4 pb-2 border-b border-limestone">
        <h2 className="text-xl font-semibold text-obsidian">{region}</h2>
        <span className="text-xs text-smoke/60 font-medium bg-mist px-2 py-0.5 rounded-full">
          {cities.length} {cities.length === 1 ? 'market' : 'markets'}
        </span>
      </div>

      {/* City cards row */}
      <div className="flex flex-wrap gap-4">
        {cities.map((market) => (
          <CityCard key={market.city} {...market} onSelect={onSelectCity} />
        ))}
      </div>
    </section>
  );
}
