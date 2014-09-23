/// <reference path="../../../lib/DefinitelyTyped/jasmine/jasmine.d.ts"/>
/// <reference path="../../../lib/DefinitelyTyped/modernizr/modernizr.d.ts"/>

import modernizr = require("modernizr");
import Config = require("../Config/Config");
import WebSocket = require("./WebSocket");

export var register = (angular, config : Config.Type, meta_api) => {

    describe("WebSocket", () => {
        var ws : WebSocket.IService;

        beforeEach(() => {
            ws = WebSocket.factory(<any>modernizr, config);
        });

        it("handles basic subscription to /adhocracy nicely.", (done) => {
            ws.register("/adhocracy", (event) => {
                done();
            });
            // this test will throw an async exception and time out if
            // an error response is sent from backend.
        });
    });
};
