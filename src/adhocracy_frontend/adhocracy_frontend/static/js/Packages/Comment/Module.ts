import * as AdhAngularHelpersModule from "../AngularHelpers/Module";
import * as AdhCredentialsModule from "../User/Module";
import * as AdhDateTimeModule from "../DateTime/Module";
import * as AdhDoneModule from "../Done/Module";
import * as AdhEmbedModule from "../Embed/Module";
import * as AdhHttpModule from "../Http/Module";
import * as AdhListingModule from "../Listing/Module";
import * as AdhMovingColumnsModule from "../MovingColumns/Module";
import * as AdhPermissionsModule from "../Permissions/Module";
import * as AdhPreliminaryNamesModule from "../PreliminaryNames/Module";
import * as AdhRateModule from "../Rate/Module";
import * as AdhResourceWidgetsModule from "../ResourceWidgets/Module";
import * as AdhTopLevelStateModule from "../TopLevelState/Module";

import * as AdhListing from "../Listing/Listing";

import * as AdhComment from "./Comment";
import * as Adapter from "./Adapter";


export var moduleName = "adhComment";

export var register = (angular) => {
    angular
        .module(moduleName, [
            AdhAngularHelpersModule.moduleName,
            AdhCredentialsModule.moduleName,
            AdhDateTimeModule.moduleName,
            AdhDoneModule.moduleName,
            AdhEmbedModule.moduleName,
            AdhHttpModule.moduleName,
            AdhListingModule.moduleName,
            AdhMovingColumnsModule.moduleName,
            AdhPermissionsModule.moduleName,
            AdhPreliminaryNamesModule.moduleName,
            AdhRateModule.moduleName,
            AdhResourceWidgetsModule.moduleName,
            AdhTopLevelStateModule.moduleName
        ])
        .directive("adhCommentListingPartial",
            ["adhConfig", "adhWebSocket", (adhConfig, adhWebSocket) =>
                new AdhListing.Listing(new Adapter.ListingCommentableAdapter()).createDirective(adhConfig, adhWebSocket)])
        .directive("adhCommentListing", ["adhConfig", "adhTopLevelState", "$location", AdhComment.adhCommentListing])
        .directive("adhCreateOrShowCommentListing", [
            "adhConfig", "adhDone", "adhHttp", "adhPreliminaryNames", "adhCredentials", AdhComment.adhCreateOrShowCommentListing])
        .directive("adhCommentResource", [
            "adhConfig", "adhHttp", "adhPermissions", "adhPreliminaryNames", "adhTopLevelState", "adhRecursionHelper", "$window", "$q",
            (adhConfig, adhHttp, adhPermissions, adhPreliminaryNames, adhTopLevelState, adhRecursionHelper, $window, $q) => {
                var adapter = new Adapter.CommentAdapter();
                var widget = new AdhComment.CommentResource(
                    adapter, adhConfig, adhHttp, adhPermissions, adhPreliminaryNames, adhTopLevelState, $window, $q);
                return widget.createRecursionDirective(adhRecursionHelper);
            }])
        .directive("adhCommentCreate", [
            "adhConfig", "adhHttp", "adhPermissions", "adhPreliminaryNames", "adhTopLevelState", "adhRecursionHelper", "$window", "$q",
            (adhConfig, adhHttp, adhPermissions, adhPreliminaryNames, adhTopLevelState, adhRecursionHelper, $window, $q) => {
                var adapter = new Adapter.CommentAdapter();
                var widget = new AdhComment.CommentCreate(
                    adapter, adhConfig, adhHttp, adhPermissions, adhPreliminaryNames, adhTopLevelState, $window, $q);
                return widget.createRecursionDirective(adhRecursionHelper);
            }])
        .directive("adhCommentColumn", ["adhConfig", AdhComment.commentColumnDirective]);
};