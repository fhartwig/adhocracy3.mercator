/// <reference path="../../../lib/DefinitelyTyped/jasmine/jasmine.d.ts"/>

import * as AdhMarkdown from "./Markdown";


export var register = () => {
    describe("Markdown", () => {
        xit("exists", () => {
            expect(AdhMarkdown).toBeDefined();
        });
    });
};
