// ver 2022.1

$( document ).ready(function() {
  // Vue otsimisäpp
  var watchExampleVM = new Vue({
    el: '#kroonika-api',
    delimiters: ['[[', ']]'],
    data: {
      question: question,
      answer: 'Otsimiseks on vaja vähemalt kolm tähte',
      wiki_artikkel_filter_url: wiki_artikkel_filter_url,
      wiki_isik_filter_url: wiki_isik_filter_url,
      wiki_organisatsioon_filter_url: wiki_organisatsioon_filter_url,
      wiki_objekt_filter_url: wiki_objekt_filter_url,
      wiki_tooltip_url: wiki_tooltip_url,
      artikkel_results: [],
      artikkel_results_count_all: 0,
      artikkel_results_count_1st_page: 0,
      isik_results: [],
      isik_results_count_all: 0,
      isik_results_count_1st_page: 0,
      organisatsioon_results: [],
      organisatsioon_results_count_all: 0,
      organisatsioon_results_count_1st_page: 0,
      objekt_results: [],
      objekt_results_count_all: 0,
      objekt_results_count_1st_page: 0,
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
      updateTooltips: function () {
        if (this.isik_results_count_all > 0 || this.organisatsioon_results_count_all > 0 || this.objekt_results_count_all > 0) {
          var elContentTooltipFields = $(".tooltip-content span");
          if (elContentTooltipFields.length) {
            // initialize tooltips
            getObjectData4tooltip(wiki_tooltip_url);
          } else {
            setTimeout(this.updateTooltips, 1000); // try again in 300 milliseconds
          }
        }
      },
      getAnswer: function () {
        // Kontrollime kas iga fraasi pikkus on vähemalt kolm tähemärki
        let max_fraasipikkus = Math.max.apply(null, this.question.trim().split(' ').map(function (fraas) {
          return fraas.length;
        }));
        if (max_fraasipikkus < 3) {
          this.answer = 'Vähemalt üks kolmetäheline sõna fraasis palun !'
          return
        }
        this.answer = 'Otsime...';
        // API url
        var isik_api_url = '/api/isik/?format=json';
        var organisatsioon_api_url = '/api/organisatsioon/?format=json';
        var objekt_api_url = '/api/objekt/?format=json';
        var artikkel_api_url = '/api/artikkel/?format=json';
        var vm = this;

        // Nullime väärtused enne uut päringut
        vm.isik_results = [];
        vm.isik_results_count_all = 0;
        vm.isik_results_count_1st_page = 0;
        vm.organisatsioon_results = [];
        vm.organisatsioon_results_count_all = 0;
        vm.organisatsioon_results_count_1st_page = 0;
        vm.objekt_results = [];
        vm.objekt_results_count_all = 0;
        vm.objekt_results_count_1st_page = 0;
        vm.artikkel_results = [];
        vm.artikkel_results_count_all = 0;
        vm.artikkel_results_count_1st_page = 0;
        vm.total_count = 0;
        let page = 1;

        // Päring isik
        axios.get(isik_api_url, {
          params: {
            sisaldab: this.question,
            page: page
          }
        })
        .then(function (response) {
          vm.isik_results_count_all = response.data.count
          vm.isik_results_count_1st_page = response.data.results.length
          vm.total_count = vm.total_count + vm.isik_results_count_all
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
        axios.get(organisatsioon_api_url, {
          params: {
            sisaldab: this.question,
            page: page
          }
        })
        .then(function (response) {
          vm.organisatsioon_results_count_all = response.data.count
          vm.organisatsioon_results_count_1st_page = response.data.results.length
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
        axios.get(objekt_api_url, {
          params: {
            sisaldab: this.question,
            page: page
          }
        })
        .then(function (response) {
          vm.objekt_results_count_all = response.data.count
          vm.objekt_results_count_1st_page = response.data.results.length
          vm.total_count = vm.total_count + vm.objekt_results_count_all
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
        axios.get(artikkel_api_url, {
          params: {
            sisaldab: this.question,
            page: page
          }
        })
        .then(function (response) {
          vm.artikkel_results_count_all = response.data.count // kokku leitud artikleid
          vm.artikkel_results_count_1st_page = response.data.results.length // esimesel leheküljel artikleid
          vm.total_count = vm.total_count + vm.artikkel_results_count_all
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.artikkel_results_count_all > 0) {
            vm.artikkel_results = response.data.results;
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });
      }
    }
  })
});