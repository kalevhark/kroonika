var watchExampleVM = new Vue({
    el: '#kroonika-api',
    data: {
      // question: '',
      answer: 'Otsimiseks on vaja vähemalt kolm tähte',
      isik_results: [],
      isik_count_results: 0,
      isik_message: '',
      organisatsioon_results: [],
      organisatsioon_count_results: 0,
      objekt_message: '',
      objekt_results: [],
      objekt_count_results: 0,
      organisatsioon_message: '',
      total_count: 0
    },
    watch: {
      // whenever question changes, this function will run
      question: function (newQuestion, oldQuestion) {
        this.answer = 'Ootan kuni lõpetad trükkimise...'
        this.debouncedGetAnswer()
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
      this.debouncedGetAnswer = _.debounce(this.getAnswer, 500)
    },
    methods: {
      getAnswer: function () {
        if (this.question.length < 3) {
          this.answer = 'Vähemalt kolm tähte palun!'
          return
        };
        this.answer = 'Otsime...';
        // var kroonika_url = 'http://' + document.getElementById("myVar").value; //  'http://192.168.1.143/kroonika/';
        console.log(kroonika_url);
        var isik_api_url = kroonika_url + '/api/isik/?format=json';
        var organisatsioon_api_url = kroonika_url + '/api/organisatsioon/?format=json';
        var objekt_api_url = kroonika_url + '/api/objekt/?format=json';
        var artikkel_api_url = kroonika_url + '/api/artikkel/?format=json';
        var vm = this;
        // Nullime väärtused enne uut päringut
        vm.isik_results = [];
        vm.isik_results_count = 0;
        vm.organisatsioon_results = [];
        vm.organisatsioon_results_count = 0;
        vm.objekt_results = [];
        vm.objekt_results_count = 0;
        vm.artikkel_results = [];
        vm.artikkel_results_count = 0;
        vm.total_count = 0;
        let page = 1;
        // Päring isik
        axios.get(isik_api_url, {
          params: {
            nimi: this.question,
            page: page
          }
        })
        .then(function (response) {
          vm.isik_results_count = response.data.count
          vm.total_count = vm.total_count + response.data.count
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.isik_results_count > 0) {
            vm.isik_results = response.data.results;
            if (vm.isik_results_count > response.data.results.length) {
              vm.isik_message = ' näitame ' + response.data.results.length;
            } else {
              vm.isik_message = '';
            };
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });
        // Päring organisatsioon
        axios.get(organisatsioon_api_url, {
          params: {
            nimi: this.question,
            page: page
          }
        })
        .then(function (response) {
          vm.organisatsioon_results_count = response.data.count
          vm.total_count = vm.total_count + response.data.count
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.organisatsioon_results_count > 0) {
            vm.organisatsioon_results = response.data.results;
            if (vm.organisatsioon_results_count > response.data.results.length) {
              vm.organisatsioon_message = ' näitame ' + response.data.results.length;
            } else {
              vm.organisatsioon_message = '';
            };
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });
        // Päring objekt
        axios.get(objekt_api_url, {
          params: {
            nimi: this.question,
            page: page
          }
        })
        .then(function (response) {
          vm.objekt_results_count = response.data.count
          vm.total_count = vm.total_count + response.data.count
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.objekt_results_count > 0) {
            vm.objekt_results = response.data.results;
            if (vm.objekt_results_count > response.data.results.length) {
              vm.objekt_message = ' näitame ' + response.data.results.length;
            } else {
              vm.objekt_message = '';
            };
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
          vm.artikkel_results_count = response.data.count
          vm.total_count = vm.total_count + response.data.count
          vm.answer = 'Leidsime ' + vm.total_count + ' vastet';
          if (vm.artikkel_results_count > 0) {
            vm.artikkel_results = response.data.results;
            if (vm.artikkel_results_count > response.data.results.length) {
              vm.artikkel_message = ' näitame ' + response.data.results.length;
            } else {
              vm.artikkel_message = '';
            };
          }
        })
        .catch(function (error) {
          vm.answer = 'Viga! API kättesaamatu. ' + error;
        });
      }
    }
})
