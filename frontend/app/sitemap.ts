import { MetadataRoute } from "next";

const BASE = "https://runlens.io";
const SAMPLE_RUN_ID = "377504bc-4de2-4322-889d-8c14819991c9";

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
    {
      url: `${BASE}/privacy`,
      changeFrequency: "monthly",
      priority: 0.3,
    },
    {
      url: `${BASE}/terms`,
      changeFrequency: "monthly",
      priority: 0.3,
    },
  ];
}
