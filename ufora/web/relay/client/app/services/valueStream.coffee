angular.module('pyfora')
  .factory 'ValueStream', ['$rootScope', ($rootScope) ->
    class ValueStream
      constructor: (values = []) ->
        @values = values
        @handlers = []
        @lastValue = undefined

      notify: (value) ->
        @appendValue(value)

      each: (handler) ->
        @handlers.unshift handler

      last: () -> @lastValue || _.last(@values)

      appendValue: (value) ->
        @values.push value
        @runQueue()

      runQueue: () ->
        _run = () =>
          _.each @values, (value) =>
            _.each @handlers, (handler) =>
              handler(value)
            @lastValue = value
        if $rootScope.$$phase
          _run()
        else
          $rootScope.$apply _run 
        @values = []
  ]



