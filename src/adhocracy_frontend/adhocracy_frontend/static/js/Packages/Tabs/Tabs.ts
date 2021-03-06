/// <reference path="../../../lib/DefinitelyTyped/angularjs/angular.d.ts"/>

import * as _ from "lodash";

import * as AdhConfig from "../Config/Config";

var pkgLocation = "/Tabs";


export interface ITabScope extends angular.IScope {
    active : boolean;
    highlighted : boolean;
    heading : string;
    classes : string;
    select() : void;
    setActive(active : boolean) : void;
    height : number;
}

export interface ITabsetScope extends angular.IScope {
    tabs : ITabScope[];
    fullWidth? : boolean;
    closedByDefault : boolean;
    buttonStyle : boolean;
}

export class TabSetController {
    constructor(private $scope : ITabsetScope, private $element, private $timeout : angular.ITimeoutService) {
        this.$scope.tabs = [];
        this.$element.find(".tabset-panes").css("height", 0);
    }

    private updateTabWidth() {
        if (this.$scope.fullWidth) {
            var value = this.$scope.tabs.length;
            if (value !== 0) {
                var tabWidth = Math.floor(100 * 10 / value) / 10;
                this.$timeout(() => {
                    this.$element.find(".tab").css("width", tabWidth + "%");
                });
            }
        }
    }

    public select(selectedTab? : ITabScope) {
        _.forEach(this.$scope.tabs, (tab : ITabScope) => {
            if (tab.active && tab !== selectedTab) {
                tab.setActive(false);
            }
        });

        if (typeof selectedTab !== "undefined") {
            selectedTab.setActive(true);
            this.$element.find(".tabset-panes").css("height", selectedTab.height);
        } else {
            this.$element.find(".tabset-panes").css("height", 0);
        }
    }

    public addTab(tab : ITabScope) {
        this.$scope.tabs.push(tab);

        // we can't run the select function on the first tab
        // since that would select it twice
        if (this.$scope.tabs.length === 1) {
            if (!this.$scope.closedByDefault) {
                tab.active = true;
            }
        } else if (tab.active) {
            this.select(tab);
        }

        this.updateTabWidth();
    }

    public removeTab(tab : ITabScope) {
        var index = this.$scope.tabs.indexOf(tab);

        // Select a new tab if the tab to be removed is selected and not destroyed
        if (tab.active && this.$scope.tabs.length > 1) {
            // If this is the last tab, select the previous tab. else, the next tab.
            var newActiveIndex = (index === this.$scope.tabs.length - 1) ? index - 1 : index + 1;
            this.select(this.$scope.tabs[newActiveIndex]);
        }
        this.$scope.tabs.splice(index, 1);

        this.updateTabWidth();
    }
}

export var tabsetDirective = (adhConfig : AdhConfig.IService) => {
    return {
        restrict: "E",
        scope: {
            fullWidth: "=?",
            closedByDefault: "=?",
            buttonStyle: "=?"
        },
        transclude: true,
        templateUrl: adhConfig.pkg_path + pkgLocation + "/tabset.html",
        controller: ["$scope", "$element", "$timeout", TabSetController]
    };
};

export var tabDirective = (adhConfig : AdhConfig.IService) => {
    return {
        require: "^tabset",
        restrict: "E",
        transclude: true,
        templateUrl: adhConfig.pkg_path + pkgLocation + "/tab.html",
        scope: {
            active: "=?",
            highlighted: "=?",
            heading: "@",
            classes: "@"
        },
        link: (scope : ITabScope, element, attrs, tabsetCtrl : TabSetController) => {
            var paneElement = element.find(".tab-pane");

            scope.height = 0;

            scope.setActive = (active : boolean) => {
                scope.active = active;
                if (active) {
                    paneElement.removeClass("ng-hide");
                    paneElement.addClass("is-active");
                    scope.height = paneElement.outerHeight();
                } else {
                    paneElement.addClass("ng-hide");
                    paneElement.removeClass("is-active");
                }
            };

            scope.select = () => {
                if (scope.active) {
                    tabsetCtrl.select();
                } else {
                    tabsetCtrl.select(scope);
                }
            };

            tabsetCtrl.addTab(scope);

            scope.setActive(scope.active);

            scope.$on("$destroy", () => {
                tabsetCtrl.removeTab(scope);
            });
        }
    };
};
