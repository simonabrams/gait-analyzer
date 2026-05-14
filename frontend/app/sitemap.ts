import { MetadataRoute } from "next";

const BASE = "https://runlens.io";
const SAMPLE_RUN_ID = "aba77d1f-2c19-4d10-808c-f4f7fd7b90e3";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: BASE,
      changeFrequency: "monthly",
      priority: 1,
    },
    {
      url: `${BASE}/about`,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${BASE}/runs/${SAMPLE_RUN_ID}`,
      changeFrequency: "monthly",
      priority: 0.6,
    },
  ];
}
