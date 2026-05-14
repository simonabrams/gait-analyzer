import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/runs", "/sign-in", "/sign-up"],
    },
    sitemap: "https://runlens.io/sitemap.xml",
  };
}
