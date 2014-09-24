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
            ws.registerErrorHandler((msg) => {
                expect(JSON.stringify(msg, null, 2)).toEqual(false);
                done();
            });

            ws.register("/adhocracy", (event) => {
                done();
            });
        });
    });
};
