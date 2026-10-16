<?php
/**
 * Driver OHIF Viewer v3 untuk SIMGOSv2 & Orthanc
 */

namespace RIS\driver\viewer;

class OHIF extends Driver {
    public function getViewer($params) {
        $config = $this->config;
        if (!empty($params["ACCESSION_NUMBER"])) {
            $url = $config["url"] . $config["queries"];
            $url = str_replace("[ACCESSION_NUMBER]", $params["ACCESSION_NUMBER"], $url);
            
            // Bypass/ambil OIDC token jika menggunakan Keycloak/OIDC
            if (isset($config["oidc"])) {
                $oidc = $config["oidc"];
                unset($oidc["url"]);

                $options = [
                    "url" => $config["oidc"]["url"],
                    "method" => "POST",
                    "header" => [
                        "Content-type: application/x-www-form-urlencoded"
                    ],
                    "data" => http_build_query($oidc),
                    "dataIsJson" => false
                ];

                $caller = clone $this->caller;
                $respon = $caller->doSendRequest($options);
                
                if ($respon && isset($respon->access_token)) {
                    $url .= "&token=" . ($respon->access_token);
                }
            }
            
            header("Location: " . $url);
            exit;
        }
    }
}
