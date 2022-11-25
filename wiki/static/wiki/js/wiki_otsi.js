// ver 2022.11

$( document ).ready(function() {
  // Vue otsimisäpp
  var watchExampleVM = new Vue({
    el: '#kroonika-api',
    delimiters: ['[[', ']]'],
    data: {
      question: question,
      answer: 'Otsimiseks on vaja vähemalt ühte kolmetähelist sõna(osa)',
      isik_api_url:'/api/isik/?format=json',
      organisatsioon_api_url: '/api/organisatsioon/?format=json',
      objekt_api_url: '/api/objekt/?format=json',
      artikkel_api_url: '/api/artikkel/?format=json',
      wiki_artikkel_filter_url: wiki_artikkel_filter_url,
      wiki_isik_filter_url: wiki_isik_filter_url,
      wiki_organisatsioon_filter_url: wiki_organisatsioon_filter_url,
      wiki_objekt_filter_url: wiki_objekt_filter_url,
      wiki_tooltip_url: wiki_tooltip_url,
      artikkel_results: [],
      artikkel_results_count_all: 0,
      artikkel_results_count_1st_page: 0,
      artikkel_results_next_page: '',
      loader_get_next_results_artiklid: false,
      isik_results: [],
      isik_results_count_all: 0,
      isik_results_count_1st_page: 0,
      isik_results_next_page: '',
      loader_get_next_results_isikud: false,
      organisatsioon_results: [],
      organisatsioon_results_count_all: 0,
      organisatsioon_results_count_1st_page: 0,
      organisatsioon_results_next_page: '',
      loader_get_next_results_organisatsioonid: false,
      objekt_results: [],
      objekt_results_count_all: 0,
      objekt_results_count_1st_page: 0,
      objekt_results_next_page: '',
      loader_get_next_results_objektid: false,
      total_count: 0
    },
    watch: {
      // whenever question changes, this function will run
      question: function (newQuestion, oldQuestion) {
        this.answer = 'Ootan kuni lõpetad trükkimise...';
        this.debouncedGetAnswer();
      }
    },
    created: function () {
      // _.debounce is a function provided by lodash to limit how
      // often a particularly expensive operation can be run.
      // In this case, we want to limit how often we access
      // api, waiting until the user has completely
      // finished typing before making the ajax request. To learn
      // more about the _.debounce function (and its cousin
      // _.throttle), visit: https://lodash.com/docs#debounce
      this.debouncedGetAnswer = _.debounce(this.getAnswer, 500);
    },
    mounted: function () {
      // toome otsingu nähtavale
      var x = document.getElementById("kroonika-api");
      x.style.opacity = "1";

      this.focusInput();
      if (this.question.length > 0) {
        this.getAnswer();
      }
    },
    methods: {
      focusInput: function () {
        // Vajalik et saada sisestusväli automaatselt aktiivseks
        this.$refs.question.focus();
      },
      clearResults: function () {
        // Nullime väärtused enne uut päringut
        this.isik_results = [];
        this.isik_results_count_all = 0;
        this.isik_results_count_1st_page = 0;
        this.isik_results_next_page = '';
        this.organisatsioon_results = [];
        this.organisatsioon_results_count_all = 0;
        this.organisatsioon_results_count_1st_page = 0;
        this.organisatsioon_results_next_page = '';
        this.objekt_results = [];
        this.objekt_results_count_all = 0;
        this.objekt_results_count_1st_page = 0;
        this.objekt_results_next_page = '';
        this.artikkel_results = [];
        this.artikkel_results_count_all = 0;
        this.artikkel_results_count_1st_page = 0;
        this.artikkel_results_next_page = '';
        this.total_count = 0;
      },
      updateTooltips: function () {
        if (this.isik_results_count_all > 0 || this.organisatsioon_results_count_all > 0 || this.objekt_results_count_all > 0) {
          vm = this;
          setTimeout(function () { // vajalik viivitus, et sisu laadida j6utakse
            var elContentTooltipFields = $(".tooltip-content span");
            if (elContentTooltipFields.length) {
              // initialize tooltips
              getObjectData4tooltip(wiki_tooltip_url);
            } else {
              setTimeout(vm.updateTooltips, 1000); // try again in 1000 milliseconds
            }
          }, 500);
        }
      },
      getAnswer: function () {
        // Kontrollime kas iga fraasi pikkus on vähemalt kolm tähemärki
        let max_fraasipikkus = Math.max.apply(null, this.question.trim().split(' ').map(function (fraas) {
          return fraas.length;
        }));
        if (max_fraasipikkus < 3) {
          this.answer = 'Otsimiseks on vaja vähemalt ühte kolmetähelist sõna(osa)';
          this.clearResults();
          return
        }
        this.answer = 'Otsime...';
        this.clearResults();
        var vm = this;
        var url = '';

        // Päring isik
        url = this.isik_api_url;
        axios.get(url, {
          params: {
            sisaldab: this.question,
          }
        })
        .then(function (response) {
          vm.isik_results_count_all = response.data.count;
          vm.isik_results_count_1st_page = response.data.results.length;
          vm.isik_results_next_page = response.data.next;
          vm.total_count = vm.total_count + vm.isik_results_count_all;
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.isik_results_count_all > 0) {
            // Kui leiti isikuid
            vm.isik_results = response.data.results;
            vm.updateTooltips();
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });

        // Päring organisatsioon
        url = this.organisatsioon_api_url;
        axios.get(url, {
          params: {
            sisaldab: this.question,
          }
        })
        .then(function (response) {
          vm.organisatsioon_results_count_all = response.data.count;
          vm.organisatsioon_results_count_1st_page = response.data.results.length;
          vm.organisatsioon_results_next_page = response.data.next;
          vm.total_count = vm.total_count + vm.organisatsioon_results_count_all
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.organisatsioon_results_count_all > 0) {
            // Kui leiti organisatsioone
            vm.organisatsioon_results = response.data.results;
            vm.updateTooltips();
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });

        // Päring objekt
        url = this.objekt_api_url;
        axios.get(url, {
          params: {
            sisaldab: this.question,
            // page: page
          }
        })
        .then(function (response) {
          vm.objekt_results_count_all = response.data.count;
          vm.objekt_results_count_1st_page = response.data.results.length;
          vm.objekt_results_next_page = response.data.next;
          vm.total_count = vm.total_count + vm.objekt_results_count_all;
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.objekt_results_count_all > 0) {
            // Kui leiti objekte
            vm.objekt_results = response.data.results;
            vm.updateTooltips();
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });

        // Päring artikkel
        url = this.artikkel_api_url;
        axios.get(url, {
          params: {
            sisaldab: this.question,
            // page: page
          }
        })
        .then(function (response) {
          vm.artikkel_results_count_all = response.data.count; // kokku leitud artikleid
          vm.artikkel_results_count_1st_page = response.data.results.length; // esimesel leheküljel artikleid
          vm.artikkel_results_next_page = response.data.next;
          vm.total_count = vm.total_count + vm.artikkel_results_count_all;
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.artikkel_results_count_all > 0) {
            vm.artikkel_results = response.data.results;
            // console.log(vm.artikkel_results);
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });
      },
      getNextResults: function (target_id) {
        var vm = this;

        switch(target_id) {
          case 'get_next_results_isikud':
            // Päring isik
            url = vm.isik_results_next_page;

            $.ajax(
              {
                url: url,
                dataType: 'json',
                timeout: 300000,
                params: {
                  sisaldab: this.question,
                },
                beforeSend: function () {
                  vm.loader_get_next_results_isikud = true;
                },
                success: function (response) {
                  vm.isik_results_count_1st_page += response.results.length;
                  vm.isik_results_next_page = response.next;
                  if (vm.isik_results_count_all > 0) {
                    // Kui leiti
                    vm.isik_results = vm.isik_results.concat(response.results);
                    vm.updateTooltips();
                  }
                },
                error: function (XMLHttpRequest, textstatus, errorThrown) {
                  console.log(textstatus);
                  vm.answer = 'Viga! API kättesaamatu. ' + textstatus;
                },
                complete: function () {
                  vm.loader_get_next_results_isikud = false;
                }
              }
            );
            break;

          case 'get_next_results_organisatsioonid':
            // Päring organisatsioonid
            url = vm.organisatsioon_results_next_page;

            $.ajax(
              {
                url: url,
                dataType: 'json',
                timeout: 300000,
                params: {
                  sisaldab: this.question,
                },
                beforeSend: function () {
                  vm.loader_get_next_results_organisatsioonid = true;
                },
                success: function (response) {
                  vm.organisatsioon_results_count_1st_page += response.results.length;
                  vm.organisatsioon_results_next_page = response.next;
                  if (vm.organisatsioon_results_count_all > 0) {
                    // Kui leiti
                    vm.organisatsioon_results = vm.organisatsioon_results.concat(response.results);
                    vm.updateTooltips();
                  }
                },
                error: function (XMLHttpRequest, textstatus, errorThrown) {
                  console.log(textstatus);
                  vm.answer = 'Viga! API kättesaamatu. ' + textstatus;
                },
                complete: function () {
                  vm.loader_get_next_results_organisatsioonid = false;
                  vm.updateTooltips();
                }
              }
            );
            break;

          case 'get_next_results_objektid':
            // Päring objektid
            url = vm.objekt_results_next_page;

            $.ajax(
              {
                url: url,
                dataType: 'json',
                timeout: 300000,
                params: {
                  sisaldab: this.question,
                },
                beforeSend: function () {
                  vm.loader_get_next_results_objektid = true;
                },
                success: function (response) {
                  vm.objekt_results_count_1st_page += response.results.length;
                  vm.objekt_results_next_page = response.next;
                  if (vm.objekt_results_count_all > 0) {
                    // Kui leiti
                    vm.objekt_results = vm.objekt_results.concat(response.results);
                    vm.updateTooltips();
                  }
                },
                error: function (XMLHttpRequest, textstatus, errorThrown) {
                  console.log(textstatus);
                  vm.answer = 'Viga! API kättesaamatu. ' + textstatus;
                },
                complete: function () {
                  vm.loader_get_next_results_objektid = false;
                }
              }
            );
            break;

          case 'get_next_results_artiklid':
            // Päring artiklid
            url = vm.artikkel_results_next_page;

            $.ajax(
              {
                url: url,
                dataType: 'json',
                timeout: 300000,
                params: {
                  sisaldab: this.question,
                },
                beforeSend: function () {
                  vm.loader_get_next_results_artiklid = true;
                  // $("#loaderDiv_get_next_results_artiklid").show();
                },
                success: function (response) {
                  vm.artikkel_results_count_1st_page += response.results.length;
                  vm.artikkel_results_next_page = response.next;
                  if (vm.artikkel_results_count_all > 0) {
                    // Kui leiti
                    vm.artikkel_results = vm.artikkel_results.concat(response.results);
                    vm.updateTooltips();
                  }
                },
                error: function (XMLHttpRequest, textstatus, errorThrown) {
                  console.log(textstatus);
                  vm.answer = 'Viga! API kättesaamatu. ' + textstatus;
                },
                complete: function () {
                  vm.loader_get_next_results_artiklid = false;
                }
              }
            );
            break;
          default:
            break;
        }
        vm.updateTooltips();
      }
    }
  })
});