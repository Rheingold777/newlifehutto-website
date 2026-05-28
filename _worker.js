export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Redirect www to apex domain
    if (url.hostname === 'www.newlifehutto.com') {
      url.hostname = 'newlifehutto.com';
      return Response.redirect(url.toString(), 301);
    }

    // Pass through to static assets
    return env.ASSETS.fetch(request);
  }
};
