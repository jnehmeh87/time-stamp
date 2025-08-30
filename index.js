const express = require('express');
const app = express();
const apiRoutes = require('./routes/api');
const helmet = require('helmet');

// Use helmet middleware for security headers
app.use(helmet());

// We need to re-add the original middleware from your project
const cors = require('cors');
app.use(cors({ optionsSuccessStatus: 200 }));
app.use(express.static('public'));

app.get('/', function (req, res) {
  res.sendFile(__dirname + '/views/index.html');
});

// Use the API routes
app.use('/api', apiRoutes);

// Error handling middleware
app.use((err, req, res, _next) => {
  console.error(err.stack);
  res.status(500).send('Something broke!');
});

// listen for requests :)
if (!module.parent) {
  const listener = app.listen(process.env.PORT || 3000, function () {
    console.log('Your app is listening on port ' + listener.address().port);
  });
}

module.exports = app; // For testing
