const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
	app.use(
		createProxyMiddleware(['/suitability','/predict','/health'], {
			target: 'http://127.0.0.1:5000',
			changeOrigin: true,
			secure: false,
			logLevel: 'silent'
		})
	);
};


