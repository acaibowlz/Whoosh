// Function to handle notification (toast) from Flask
function handleNotification() {
  setTimeout(function () {
    var notification = document.getElementById("notification");
    if (notification) {
      notification.style.opacity = "0";
      setTimeout(function () {
        notification.style.display = "none";
      }, 300);
    }
  }, 3000);
}

// Function to update the year tag in the footer
function updateCurrentYear() {
  var currentDate = new Date();
  var currentYear = currentDate.getFullYear();
  var yearTag = document.getElementById("yearTag");
  if (yearTag) {
    yearTag.innerHTML = currentYear;
  }
  var yearTagMobile = document.getElementById("yearTagMobile");
  if (yearTagMobile) {
    yearTagMobile.innerHTML = currentYear;
  }
}

// Function to convert UTC time from server side to local time from client side
function convertUTCToLocal() {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const formatSettings = {
    "utc-to-local-long": {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    },
    "utc-to-local-medium": {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    },
    "utc-to-local-short": {
      timeZone: timezone,
      year: "numeric",
      month: "long",
      day: "numeric",
    },
  };

  Object.keys(formatSettings).forEach((className) => {
    const elements = document.querySelectorAll("." + className);
    elements.forEach((element) => {
      const utcDateString = element.textContent.trim();
      const date = new Date(utcDateString);

      if (className === "utc-to-local-long") {
        const optionsDate = {
          timeZone: timezone,
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        };
        const optionsTime = {
          timeZone: timezone,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        };
        const localDate = date.toLocaleDateString("en-CA", optionsDate);
        const localTime = date.toLocaleTimeString("en-CA", optionsTime);
        element.textContent = `${localDate} ${localTime}`;
      } else {
        const localDateString = date.toLocaleString(
          "en-CA",
          formatSettings[className],
        );
        element.textContent = localDateString;
      }
    });
  });
}

// Function to format count numbers of views, comments
function formatCounts() {
  const elements = document.querySelectorAll(".count");

  elements.forEach((element) => {
    const number = parseFloat(element.innerHTML);

    if (!isNaN(number)) {
      element.innerHTML = number.toLocaleString();
    }
  });
}

// Function to set content container height
function setContentMinHeight() {
  const navbar = document.querySelector(".navbar");
  const cover = document.querySelector(".cover");
  const bottomNav = document.querySelector(".bottom-nav");
  const footer = document.querySelector(".footer");

  const navbarHeight = navbar ? navbar.offsetHeight : 0;
  const coverHeight = cover ? cover.offsetHeight : 0;
  const bottomNavHeight = bottomNav ? bottomNav.offsetHeight : 0;
  const footerHeight = footer ? footer.offsetHeight : 0;
  const totalHeights =
    navbarHeight + coverHeight + bottomNavHeight + footerHeight;

  const content = document.querySelector(".content");
  content.style.minHeight = `calc(102vh - ${totalHeights}px)`;
}

function setCoverHeight() {
  const cover = document.querySelector(".cover");
  const width = cover.offsetWidth; // numeric width in px
  cover.style.height = `${(9 / 21) * width}px`;
}

// Attach all event listeners and initializations inside DOMContentLoaded
document.addEventListener("DOMContentLoaded", function () {
  handleNotification();
  updateCurrentYear();
  convertUTCToLocal();
  formatCounts();
  setCoverHeight();
  setContentMinHeight();

  window.addEventListener("resize", setCoverHeight);
  window.addEventListener("resize", setContentMinHeight);
});
