const handleDate = (req, res) => {
  const dateString = req.params.date;
  let date;

  if (!dateString) {
    // Handle empty date parameter
    date = new Date();
  } else {
    // If the string consists only of digits, treat it as a Unix timestamp
    if (/^\d+$/.test(dateString)) {
      date = new Date(parseInt(dateString));
    } else {
      // Otherwise, treat it as a date string
      date = new Date(dateString);
    }
  }

  // Check for invalid date
  if (date.toString() === 'Invalid Date') {
    return res.json({ error: 'Invalid Date' });
  }

  // Respond with the JSON object
  res.json({
    unix: date.getTime(),
    utc: date.toUTCString(),
  });
};

module.exports = {
  handleDate,
};
