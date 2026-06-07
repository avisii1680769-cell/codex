import { BoTTubeClient } from "../dist/client.js";

const client = new BoTTubeClient();

const stats = await client.stats();
const trending = await client.trending();
const search = await client.search("retro computing");

console.log(JSON.stringify({
  statsType: typeof stats,
  trendingType: typeof trending,
  searchType: typeof search,
  statsKeys: Object.keys(stats || {}).slice(0, 8),
  trendingKeys: Object.keys(trending || {}).slice(0, 8),
  searchKeys: Object.keys(search || {}).slice(0, 8),
}, null, 2));
