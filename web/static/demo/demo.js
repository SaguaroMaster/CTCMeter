demo = {
  initPickColor: function() {
    $('.pick-class-label').click(function() {
      var new_class = $(this).attr('new-class');
      var old_class = $('#display-buttons').attr('data-class');
      var display_div = $('#display-buttons');
      if (display_div.length) {
        var display_buttons = display_div.find('.btn');
        display_buttons.removeClass(old_class);
        display_buttons.addClass(new_class);
        display_div.attr('data-class', new_class);
      }
    });
  },

  initChartsPages: function() {
    chartColor = "#FFFFFF";

    ctx = document.getElementById('power-today').getContext("2d");

    myChart = new Chart(ctx, {
      type: 'line',
      
      data: {
        labels: JSON.parse(document.getElementById("power-today").dataset.graphdatax),
        
        datasets: [{
            label: 'Line Speed [m/min]',
            borderColor: "#5fa383",
            backgroundColor: "#85e6ba",
            pointRadius: 2,
            pointHoverRadius: 0,
            borderWidth: 3,
            data: JSON.parse(document.getElementById("power-today").dataset.graphdatay)
          }
        ]
      },
      options: {
        responsive: true,
        legend: {
          display: true
        },

        tooltips: {
          enabled: true
        },

        scales: {
          y: [{

            ticks: {
              fontColor: "#9f9f9f",
              beginAtZero: true,
              maxTicksLimit: 4,
              //padding: 20
            },
            gridLines: {
              drawBorder: false,
              zeroLineColor: "#ccc",
              color: 'rgba(255,255,255,0.05)',
              display: true
            }

          }],

          x: [{
            barPercentage: 1.6,
            gridLines: {
              drawBorder: false,
              color: 'rgba(255,255,255,0.1)',
              zeroLineColor: "transparent",
              display: true,
            },
            ticks: {
              padding: 20,
              fontColor: "#9f9f9f"
            }
          }]
        },
      }
    });

    ctx = document.getElementById('daily-energy').getContext("2d");

    myChart = new Chart(ctx, {
      type: 'bar',
      
      data: {
        labels: JSON.parse(document.getElementById("daily-energy").dataset.graphdatax),
        
        datasets: [
          {
            label: 'Length [m]',
            borderColor: "#facf73",
            backgroundColor: "#facf73",
            pointRadius: 0,
            pointHoverRadius: 0,
            borderWidth: 3,
            data: JSON.parse(document.getElementById("daily-energy").dataset.graphdatay)
          },
          
        ]
      },
      options: {
        legend: {
          display: true,
        },
        tooltips: {
          enabled: true
        },

        scales: {
          y: [{
            
            ticks: {
              fontColor: "#9f9f9f",
              beginAtZero: true,
              maxTicksLimit: 4,
              //padding: 20
              
            },
            gridLines: {
              drawBorder: true,
              zeroLineColor: "#ccc",
              color: 'rgba(255,255,255,0.05)',
              display: true
            },
            stacked: true

          }],

          x: [{
            barPercentage: 1.6,
            gridLines: {
              drawBorder: false,
              color: 'rgba(255,255,255,0.1)',
              zeroLineColor: "transparent",
              display: true,
            },
            ticks: {
              padding: 20,
              fontColor: "#9f9f9f"
            },
            stacked: true
          }],
          xAxes: [{
            stacked: true,
          }]
        },
      }
    });
    
    ctx = document.getElementById('average-energy').getContext("2d");

    myChart = new Chart(ctx, {
      type: 'line',
      
      data: {
        labels: JSON.parse(document.getElementById("average-energy").dataset.graphdatax),
        
        datasets: [{
            label: 'Length [m]',
            borderColor: "#7428f7",
            backgroundColor: "#ad7dff",
            pointRadius: 2,
            pointHoverRadius: 0,
            borderWidth: 3,
            data: JSON.parse(document.getElementById("average-energy").dataset.graphdatay)
          }
        ]
      },
      options: {
        responsive: true,
        legend: {
          display: true
        },

        tooltips: {
          enabled: true
        },

        scales: {
          y: [{

            ticks: {
              fontColor: "#9f9f9f",
              beginAtZero: true,
              maxTicksLimit: 4,
            },
            gridLines: {
              drawBorder: false,
              zeroLineColor: "#ccc",
              color: 'rgba(255,255,255,0.05)',
              display: true
            }

          }],

          x: [{
            barPercentage: 1.6,
            gridLines: {
              drawBorder: false,
              color: 'rgba(255,255,255,0.1)',
              zeroLineColor: "transparent",
              display: true,
            },
            ticks: {
              padding: 20,
              fontColor: "#9f9f9f"
            }
          }]
        },
      }
    });

    ctx = document.getElementById('total-energy').getContext("2d");

    myChart = new Chart(ctx, {
      type: 'line',
      
      data: {
        labels: JSON.parse(document.getElementById("total-energy").dataset.graphdatax),
        
        datasets: [
          {
            label: 'Alarm setting [m]',
            borderColor: "#1cc2ff",
            backgroundColor: "#9ee0f7",
            pointRadius: 0,
            pointHoverRadius: 0,
            borderWidth: 3,
            data: JSON.parse(document.getElementById("total-energy").dataset.graphdatay)
          },
          
        ]
      },
      options: {
        
        legend: {
          display: true
        },

        tooltips: {
          enabled: true
        },

        scales: {
          y: [{
            ticks: {
              fontColor: "#9f9f9f",
              beginAtZero: true,
              maxTicksLimit: 4,
              //padding: 20
            },
            gridLines: {
              drawBorder: false,
              zeroLineColor: "#ccc",
              color: 'rgba(255,255,255,0.05)',
              display: true
            },
            

          }],

          x: [{
            barPercentage: 1.6,
            gridLines: {
              drawBorder: false,
              color: 'rgba(255,255,255,0.1)',
              zeroLineColor: "transparent",
              display: true,
            },
            ticks: {
              padding: 20,
              fontColor: "#9f9f9f"
            },
            stacked: true,
          }],
          xAxes: [{
            stacked: true,
            scaleLabel: {
              display: true,
              labelString: 'Date [Month]'
            }
          }],

        },
      }
    });
  },

  showNotification: function(from, align) {
    color = 'primary';

    $.notify({
      icon: "nc-icon nc-bell-55",
      message: "Welcome to <b>Paper Dashboard</b> - a beautiful bootstrap dashboard for every web developer."

    }, {
      type: color,
      timer: 8000,
      placement: {
        from: from,
        align: align
      }
    });
  },

  showNotificationUpdate: function(from, align) {
    color = 'warning';

    $.notify({
      icon: "nc-icon nc-bell-55",
      message: "<b>Updating...</b> This usually takes around 5 seconds."

    }, {
      type: color,
      timer: 8000,
      placement: {
        from: from,
        align: align
      }
    });
  },

  showNotificationReboot: function(from, align) {
    color = 'danger';

    $.notify({
      icon: "nc-icon nc-bell-55",
      message: "<b>Rebooting...</b> This usually takes around 1 minute."

    }, {
      type: color,
      timer: 8000,
      placement: {
        from: from,
        align: align
      }
    });
  }

};