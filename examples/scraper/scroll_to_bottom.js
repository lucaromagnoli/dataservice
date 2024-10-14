(async () => {
  const scroll = async () => {
    const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
    const scrollHeight = () => document.body.scrollHeight;
    const start = 0;
    const shouldStop = (position) => position > scrollHeight();
    const increment = 100;
    const delayTime = 100;
    console.error(start, shouldStop(start), increment);
    for (let i = start; !shouldStop(i); i += increment) {
      window.scrollTo(0, i);
      await delay(delayTime);
    }
  };

  await scroll();
})();
