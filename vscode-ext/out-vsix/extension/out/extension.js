"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
const vscode = __importStar(require("vscode"));
function activate(context) {
    const provider = vscode.languages.registerCompletionItemProvider({ language: 'c+', scheme: 'file' }, {
        provideCompletionItems(document, position) {
            const completionItems = [];
            const f_print = new vscode.CompletionItem('print', vscode.CompletionItemKind.Function);
            f_print.detail = 'A declaration of printf';
            f_print.insertText = new vscode.SnippetString('print("$1");');
            completionItems.push(f_print);
            const f_write = new vscode.CompletionItem('write', vscode.CompletionItemKind.Function);
            f_write.detail = 'A declaration of write';
            f_write.insertText = new vscode.SnippetString('write($1, "$2", $3);');
            completionItems.push(f_write);
            const f_exit = new vscode.CompletionItem('exit', vscode.CompletionItemKind.Function);
            f_exit.detail = 'A declaration of exit';
            f_exit.insertText = new vscode.SnippetString('exit($1);');
            completionItems.push(f_exit);
            const f_fork = new vscode.CompletionItem('fork', vscode.CompletionItemKind.Function);
            f_fork.detail = 'A declaration of fork';
            f_fork.insertText = new vscode.SnippetString('fork();');
            completionItems.push(f_fork);
            const f_execve = new vscode.CompletionItem('execve', vscode.CompletionItemKind.Function);
            f_execve.detail = 'A declaration of execve';
            f_execve.insertText = new vscode.SnippetString('execve("$1", $2, $3);');
            completionItems.push(f_execve);
            const f_malloc = new vscode.CompletionItem('malloc', vscode.CompletionItemKind.Function);
            f_malloc.detail = 'A declaration of malloc';
            f_malloc.insertText = new vscode.SnippetString('malloc($1);');
            completionItems.push(f_malloc);
            /*const f_free = new vscode.CompletionItem('free', vscode.CompletionItemKind.Function);
            f_print.detail = 'A declaration of free';
            f_print.insertText = new vscode.SnippetString('free($1);');
            completionItems.push(f_print);*/
            return completionItems;
        }
    });
    context.subscriptions.push(provider);
}
