const express = require('express');
const router = express.Router();
const dateController = require('../controllers/dateController');

router.get('/hello', (req, res) => {
  res.json({ greeting: 'hello API' });
});

router.get('/:date?', dateController.handleDate);

module.exports = router;
