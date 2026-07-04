import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Only the runs list, run comparison, and account pages require sign-in.
// Individual run detail pages (/runs/[id]) are intentionally public
// so share links and the sample run work without auth.
const isProtectedRoute = createRouteMatcher(["/runs", "/runs/compare", "/account(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
